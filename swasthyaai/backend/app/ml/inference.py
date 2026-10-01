from pathlib import Path


import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

MODEL_DIR = BASE_DIR / "ml"

DEVICE = torch.device("cpu")

IMAGE_SIZE = 456

MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]


# ============================================================
# CLASS DEFINITIONS
# ============================================================

JAUNDICE_CLASSES = [
    "Jaundice",
    "Normal_Eye",
]

SKIN_CLASSES = [
    "AD",
    "CD",
    "EC",
    "SC",
    "SD",
    "TC",
]

# Registered model versions
JAUNDICE_MODEL_VERSION = "jaundice-efficientnet-b5-v1"
SKIN_MODEL_VERSION = "skin-efficientnet-b5-v1"


# ============================================================
# IMAGE PREPROCESSING
# ============================================================

# ============================================================
# LETTERBOX PREPROCESSING
# ============================================================

def letterbox_image(
    image: Image.Image,
    size: int = IMAGE_SIZE,
    fill=(123, 116, 104)
) -> Image.Image:

    image = image.convert("RGB")

    width, height = image.size

    scale = min(
        size / width,
        size / height
    )

    new_width = round(width * scale)
    new_height = round(height * scale)

    image = image.resize(
        (new_width, new_height),
        Image.Resampling.BICUBIC
    )

    canvas = Image.new(
        "RGB",
        (size, size),
        fill
    )

    left = (size - new_width) // 2
    top = (size - new_height) // 2

    canvas.paste(
        image,
        (left, top)
    )

    return canvas


transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(
        mean=MEAN,
        std=STD
    ),
])


# ============================================================
# MODEL CREATION
# ============================================================

def create_efficientnet_b5(num_classes: int):

    model = models.efficientnet_b5(
        weights=None
    )

    # Replace final classifier
    model.classifier[1] = nn.Linear(
        model.classifier[1].in_features,
        num_classes
    )

    return model


# ============================================================
# MODEL LOADING
# ============================================================

def load_model(
    model_path: Path,
    num_classes: int
):

    checkpoint = torch.load(
        model_path,
        map_location=DEVICE,
        weights_only=False
    )

    model = create_efficientnet_b5(
        num_classes=num_classes
    )

    model.load_state_dict(
        checkpoint["model_state_dict"]
    )

    model.to(DEVICE)

    model.eval()

    return model


# ============================================================
# LOAD JAUNDICE MODEL
# ============================================================

JAUNDICE_MODEL_PATH = (
    MODEL_DIR
    / "jaundice"
    / "jaundice_efficientnet_b5_final.pth"
)

jaundice_model = load_model(
    JAUNDICE_MODEL_PATH,
    num_classes=2
)


# ============================================================
# LOAD SKIN MODEL
# ============================================================

SKIN_MODEL_PATH = (
    MODEL_DIR
    / "skin"
    / "skin_efficientnet_b5_final.pth"
)

skin_model = load_model(
    SKIN_MODEL_PATH,
    num_classes=6
)


# ============================================================
# PREDICTION FUNCTION
# ============================================================

def predict(
    image_path: str,
    screening_type: str
):

    screening_type = screening_type.lower().strip()

    # --------------------------------------------------------
    # Select model
    # --------------------------------------------------------

    if screening_type == "jaundice":

        model = jaundice_model
        class_names = JAUNDICE_CLASSES
        model_version = JAUNDICE_MODEL_VERSION

    elif screening_type == "skin":

        model = skin_model
        class_names = SKIN_CLASSES
        model_version = SKIN_MODEL_VERSION

    else:

        raise ValueError(
            f"Unsupported screening type: {screening_type}"
        )

    # --------------------------------------------------------
    # Load image
    # --------------------------------------------------------
    image = Image.open(image_path).convert("RGB")
    image = letterbox_image(image)

    # --------------------------------------------------------
    # Preprocess
    # --------------------------------------------------------

    image_tensor = transform(image)

    # Add batch dimension
    image_tensor = image_tensor.unsqueeze(0)

    image_tensor = image_tensor.to(DEVICE)

    # --------------------------------------------------------
    # Inference
    # --------------------------------------------------------

    with torch.no_grad():

        outputs = model(image_tensor)

        probabilities = torch.softmax(
            outputs,
            dim=1
        )

        confidence, predicted_index = torch.max(
            probabilities,
            dim=1
        )

    # --------------------------------------------------------
    # Convert result
    # --------------------------------------------------------

    predicted_index = predicted_index.item()

    confidence = confidence.item()

    prediction = class_names[predicted_index]

    return {
        "prediction": prediction,
        "confidence": confidence,
        "class_index": predicted_index,
        "screening_type": screening_type,
        "model_version": model_version,
    }
