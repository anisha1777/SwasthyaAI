from pathlib import Path

import numpy as np
import torch
from PIL import Image

from app.ml.inference import (
    DEVICE,
    JAUNDICE_CLASSES,
    SKIN_CLASSES,
    jaundice_model,
    skin_model,
    transform,
)


# ============================================================
# GRAD-CAM
# ============================================================

def generate_gradcam(
    image_path: str,
    screening_type: str,
    target_class_index: int,
    output_path: str,
) -> str:
    """
    Generate a Grad-CAM visualization for a screening image.

    Supported:
        JAUNDICE
        SKIN

    Returns:
        Path of the generated Grad-CAM image.
    """

    screening_type = screening_type.strip().lower()

    # --------------------------------------------------------
    # Select model
    # --------------------------------------------------------

    if screening_type == "jaundice":
        model = jaundice_model
        class_names = JAUNDICE_CLASSES

    elif screening_type == "skin":
        model = skin_model
        class_names = SKIN_CLASSES

    else:
        raise ValueError(
            f"Grad-CAM is not supported for '{screening_type}'."
        )

    # --------------------------------------------------------
    # Validate class index
    # --------------------------------------------------------

    if target_class_index < 0:
        raise ValueError("Invalid target class index.")

    if target_class_index >= len(class_names):
        raise ValueError(
            f"Target class index {target_class_index} "
            f"is outside the available class range."
        )

    # --------------------------------------------------------
    # Prepare model
    # --------------------------------------------------------

    model.eval()

    # EfficientNet-B5 final convolutional feature block.
    #
    # torchvision EfficientNet structure:
    #
    # model.features
    #     ...
    #     [-1] -> final feature block
    #
    target_layer = model.features[-1]

    activations = []
    gradients = []

    # --------------------------------------------------------
    # Forward hook
    # --------------------------------------------------------

    def forward_hook(module, module_input, module_output):
        activations.append(
            module_output.detach()
        )

    # --------------------------------------------------------
    # Backward hook
    # --------------------------------------------------------

    def backward_hook(
        module,
        grad_input,
        grad_output,
    ):
        gradients.append(
            grad_output[0].detach()
        )

    forward_handle = target_layer.register_forward_hook(
        forward_hook
    )

    backward_handle = target_layer.register_full_backward_hook(
        backward_hook
    )

    try:

        # ----------------------------------------------------
        # Load image
        # ----------------------------------------------------

        image = Image.open(
            image_path
        ).convert("RGB")

        # ----------------------------------------------------
        # Apply same preprocessing used by inference.py
        # ----------------------------------------------------

        image_tensor = transform(
            image
        ).unsqueeze(0).to(DEVICE)

        # ----------------------------------------------------
        # Forward pass
        # ----------------------------------------------------

        model.zero_grad(set_to_none=True)

        with torch.enable_grad():

            outputs = model(
                image_tensor
            )

            # ------------------------------------------------
            # Select target class
            # ------------------------------------------------

            target_score = outputs[
                0,
                target_class_index
            ]

            # ------------------------------------------------
            # Backward pass
            # ------------------------------------------------

            target_score.backward()

        # ----------------------------------------------------
        # Validate hooks
        # ----------------------------------------------------

        if not activations:
            raise RuntimeError(
                "Grad-CAM activation hook did not capture output."
            )

        if not gradients:
            raise RuntimeError(
                "Grad-CAM gradient hook did not capture gradient."
            )

        # ----------------------------------------------------
        # Get activation and gradient
        # ----------------------------------------------------

        activation = activations[-1][0]

        gradient = gradients[-1][0]

        # ----------------------------------------------------
        # Global average pooling of gradients
        # ----------------------------------------------------

        weights = gradient.mean(
            dim=(1, 2),
            keepdim=True,
        )

        # ----------------------------------------------------
        # Weighted feature maps
        # ----------------------------------------------------

        cam = (
            weights * activation
        ).sum(
            dim=0
        )

        # ----------------------------------------------------
        # ReLU
        # ----------------------------------------------------

        cam = torch.relu(cam)

        # ----------------------------------------------------
        # Convert to NumPy
        # ----------------------------------------------------

        cam = cam.detach().cpu().numpy()

        # ----------------------------------------------------
        # Normalize CAM
        # ----------------------------------------------------

        cam_min = cam.min()
        cam_max = cam.max()

        if cam_max - cam_min > 1e-8:

            cam = (
                cam - cam_min
            ) / (
                cam_max - cam_min
            )

        else:

            cam = np.zeros_like(
                cam
            )

        # ----------------------------------------------------
        # Resize heatmap to original image
        # ----------------------------------------------------

        original_width, original_height = image.size

        heatmap_image = Image.fromarray(
            np.uint8(
                cam * 255
            ),
            mode="L",
        )

        heatmap_image = heatmap_image.resize(
            (
                original_width,
                original_height,
            ),
            Image.Resampling.BILINEAR,
        )

        heatmap = np.array(
            heatmap_image
        ).astype(
            np.float32
        ) / 255.0

        # ----------------------------------------------------
        # Create RGB heatmap
        #
        # Low activation:
        #     blue
        #
        # Medium:
        #     yellow
        #
        # High:
        #     red
        # ----------------------------------------------------

        heatmap_rgb = np.zeros(
            (
                original_height,
                original_width,
                3,
            ),
            dtype=np.uint8,
        )

        # Red channel
        heatmap_rgb[:, :, 0] = np.uint8(
            np.clip(
                255 * heatmap * 2,
                0,
                255,
            )
        )

        # Green channel
        heatmap_rgb[:, :, 1] = np.uint8(
            np.clip(
                255 * (1 - np.abs(heatmap - 0.5) * 2),
                0,
                255,
            )
        )

        # Blue channel
        heatmap_rgb[:, :, 2] = np.uint8(
            np.clip(
                255 * (1 - heatmap) * 2,
                0,
                255,
            )
        )

        heatmap_color = Image.fromarray(
            heatmap_rgb,
            mode="RGB",
        )

        # ----------------------------------------------------
        # Create overlay
        # ----------------------------------------------------

        original_rgb = image.convert(
            "RGB"
        )

        overlay = Image.blend(
            original_rgb,
            heatmap_color,
            alpha=0.45,
        )

        # ----------------------------------------------------
        # Add prediction label
        # ----------------------------------------------------

        try:

            from PIL import ImageDraw

            draw = ImageDraw.Draw(
                overlay
            )

            label = (
                f"Class: "
                f"{class_names[target_class_index]}"
            )

            draw.rectangle(
                (
                    0,
                    0,
                    min(
                        original_width,
                        500,
                    ),
                    35,
                ),
                fill=(0, 0, 0),
            )

            draw.text(
                (
                    8,
                    8,
                ),
                label,
                fill=(255, 255, 255),
            )

        except Exception:
            # Label is optional.
            pass

        # ----------------------------------------------------
        # Save output
        # ----------------------------------------------------

        output = Path(
            output_path
        )

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        overlay.save(
            output,
            format="JPEG",
            quality=95,
        )

        return str(output)

    finally:

        # ----------------------------------------------------
        # Always remove hooks
        # ----------------------------------------------------

        forward_handle.remove()
        backward_handle.remove()
