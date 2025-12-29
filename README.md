# ImageFilter

A Python toolkit for sorting, filtering, and classifying images based on multiple criteria including NSFW probability, image quality scores, metadata, and gender classification. Primarily designed for AI-generated images from Stable Diffusion but works with any image collection.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Available Scripts](#available-scripts)
- [Usage](#usage)
- [Configuration](#configuration)
- [Filtering Types](#filtering-types)
- [Scoring Models](#scoring-models)
- [Future Improvements](#future-improvements)
- [Support](#support)
- [Credits](#credits)

## Features

- **NSFW Detection**: Automatically detect and sort images by NSFW probability using OpenNSFW2
- **Image Quality Scoring**: Score images using 38 different Keras pre-trained models
- **Metadata Extraction**: Extract and store image metadata (prompts, parameters, hashes) in MySQL database
- **Gender Classification**: Classify images by gender using custom-trained models
- **Stable Diffusion Filtering**: Filter images by model name and generation parameters
- **Flexible Organization**: Move or copy images to organized folder structures

## Requirements

- Python 3.7+
- Windows 10 or Linux
- MySQL (for metadata extraction features)

## Installation

Install all required dependencies:

```bash
pip install pillow tensorflow keras PyQt5 opennsfw2 mysql-connector-python PyYAML
```

**Dependency Overview:**
- `pillow` - Image processing and manipulation
- `tensorflow` & `keras` - Deep learning models for scoring and classification
- `PyQt5` - GUI file/folder selection dialogs
- `opennsfw2` - NSFW content detection
- `mysql-connector-python` - Database connectivity for metadata storage
- `PyYAML` - Configuration file parsing

## Available Scripts

### 1. nsfw-score-and-model-filter.py
Main filtering script that combines NSFW detection, quality scoring, model filtering, and parameter filtering.

**Features:**
- Filter by NSFW probability (9 ranges from 0.0-1.0)
- Score images using 38+ Keras models
- Filter by Stable Diffusion model name
- Filter by positive prompt parameters
- Autonomous mode with JSON configuration

### 2. nsfw-filter.py
Lightweight script for quick NSFW probability checks on individual images.

### 3. metadata_extraction.py
Extracts metadata from Stable Diffusion generated images and stores in MySQL database.

**Extracted Information:**
- Positive/negative prompts
- Generation parameters (steps, sampler, CFG scale, seed, model)
- File information (name, size, creation date)
- Hash values (MD5, SHA1, SHA256)
- Optional NSFW probability

### 4. gender-classification.py
Classifies images into gender categories (male, female, both, neither) using custom-trained models.

### 5. gender-training.py
Training script for creating custom gender classification models using transfer learning.

## Usage

### Basic NSFW Filtering

```bash
python nsfw-filter.py
```
Prompts for image path and displays NSFW probability.

### Advanced Filtering (Interactive Mode)

```bash
python nsfw-score-and-model-filter.py
```
Follow the interactive prompts to:
1. Select input/output folders
2. Choose filtering mode (NSFW, Score, Model, Parameters)
3. Select scoring model
4. Configure move/copy behavior

### Autonomous Filtering

Edit `nsfw-score-and-model-filter_config.json`:
```json
{
  "autonomous": "True",
  "input_folder": "/path/to/images",
  "output_folder": "/path/to/output",
  "move_or_copy": 2,
  "mode": 1,
  "model_type": 1,
  "score_or_class": "s"
}
```

Then run:
```bash
python nsfw-score-and-model-filter.py
```

### Metadata Extraction

1. Configure `metadata_config.yml`:
```yaml
host: localhost
user: your_user
password: your_password
database_name: image_metadata
table_name: images
image_folder: /path/to/images
use_yesterday: false
nsfw_probability: true
prefix: SD_
```

2. Run the extraction:
```bash
python metadata_extraction.py
```

### Gender Classification

```bash
python gender-classification.py
```
Select input folder, output folder, model file (.h5), and scoring model type.

## Configuration

### nsfw-score-and-model-filter_config.json

| Parameter | Type | Description |
|-----------|------|-------------|
| `autonomous` | string | "True" for config-based execution, "False" for interactive |
| `input_folder` | string | Path to source images |
| `output_folder` | string | Path for sorted output |
| `move_or_copy` | int | 1 = move, 2 = copy |
| `mode` | int | 1 = NSFW, 2 = Score, 3 = Model, 4 = Parameters |
| `model_type` | int | 1-38 (see Scoring Models section) |
| `score_or_class` | string | "s" = score, "c" = class |
| `experimental` | string | "y"/"n" - enable experimental features |
| `own_parameters` | string | "y"/"n" - use custom parameters |
| `parameters` | array | List of parameters to filter by |
| `strict_parameters` | string | "y" = match all, "n" = match any |
| `split_words` | string | "True"/"False" - split parameters into words |

### metadata_config.yml

| Parameter | Type | Description |
|-----------|------|-------------|
| `host` | string | MySQL server hostname |
| `user` | string | Database username |
| `password` | string | Database password |
| `database_name` | string | Target database name |
| `table_name` | string | Target table name |
| `image_folder` | string | Folder to scan for images |
| `use_yesterday` | boolean | Process yesterday's folder only |
| `nsfw_probability` | boolean | Calculate NSFW scores |
| `prefix` | string | Log file prefix |

## Filtering Types

### 1. NSFW Probability

Images are sorted into 9 probability ranges:
- 0.0 - 0.2 (Safe)
- 0.2 - 0.4
- 0.4 - 0.6
- 0.6 - 0.8
- 0.8 - 0.9
- 0.9 - 0.95
- 0.95 - 0.99
- 0.99 - 0.995
- 0.995 - 1.0 (Explicit)

Uses the OpenNSFW2 model for detection, providing accurate probability scores for adult content.

### 2. Score Filtering

Images are scored based on aesthetic quality or predicted class using pre-trained models. Scores are sorted into ranges depending on the model type:
- Small models (0.0-1.0): 5 ranges
- Big models (0-10): 5 ranges

### 3. Model Filtering

Filter Stable Diffusion images by the model used for generation (extracted from metadata).

### 4. Parameter Filtering

Filter by positive prompt keywords. Supports:
- Custom parameter lists
- Match any or match all modes
- Word splitting for partial matches

## Scoring Models

38 pre-trained Keras models are available for image quality assessment:

| # | Model | Input Size | Type |
|---|-------|------------|------|
| 1 | Xception | 299x299 | High accuracy |
| 2 | VGG16 | 224x224 | Classic architecture |
| 3 | VGG19 | 224x224 | Classic architecture |
| 4 | ResNet50 | 224x224 | Residual networks |
| 5 | ResNet50V2 | 224x224 | Residual networks v2 |
| 6 | ResNet101 | 224x224 | Residual networks |
| 7 | ResNet101V2 | 224x224 | Residual networks v2 |
| 8 | ResNet152 | 224x224 | Residual networks |
| 9 | ResNet152V2 | 224x224 | Residual networks v2 |
| 10 | InceptionV3 | 299x299 | Inception architecture |
| 11 | InceptionResNetV2 | 299x299 | Hybrid architecture |
| 12 | MobileNet | 224x224 | Lightweight |
| 13 | MobileNetV2 | 224x224 | Lightweight v2 |
| 14 | DenseNet121 | 224x224 | Dense connections |
| 15 | DenseNet169 | 224x224 | Dense connections |
| 16 | DenseNet201 | 224x224 | Dense connections |
| 17 | NASNetMobile | 224x224 | Neural architecture search |
| 18 | NASNetLarge | 331x331 | Neural architecture search |
| 19-26 | EfficientNetB0-B7 | 224-600 | Efficient scaling |
| 27-33 | EfficientNetV2B0-V2L | 224-480 | Efficient v2 |
| 34-38 | ConvNeXt (Tiny-XLarge) | 224x224 | Modern ConvNet |

> More information: [Keras Applications Documentation](https://keras.io/api/applications/)

**Model Selection Tips:**
- **Fast processing**: Use MobileNet, MobileNetV2, or EfficientNetB0
- **High accuracy**: Use Xception, InceptionV3, or EfficientNetB7
- **Balanced**: Use ResNet50, DenseNet121, or EfficientNetB3

## Future Improvements

### Planned Features
- [ ] Add class names for folder organization
- [ ] Better parameter integration modes
- [ ] Enhanced error handling and user feedback
- [ ] Custom score/NSFW ranges with decimal precision
- [ ] Automatic dependency installation script
- [ ] Web-based interface option
- [ ] Batch processing progress indicators
- [ ] Support for additional image formats (WebP, AVIF)

### Under Consideration
- [ ] Support for other AI image generation tools (Midjourney, DALL-E metadata)
- [ ] Video frame extraction and filtering
- [ ] Cloud storage integration (S3, Google Cloud Storage)
- [ ] REST API for remote filtering

## Support

### Bug Reports
Use [GitHub Issues](https://github.com/gabriel20xx/ImageFilter/issues) for bug reports and feature requests.

**When reporting bugs, please include:**
- Operating system and Python version
- Complete error message or stack trace
- Steps to reproduce the issue
- Sample configuration files (remove sensitive data)
- Expected vs actual behavior

### Common Issues

**Q: Getting "No module named 'opennsfw2'" error**  
A: Run `pip install opennsfw2`

**Q: TensorFlow/Keras model loading is slow**  
A: First run downloads models from the internet. Subsequent runs use cached models.

**Q: MySQL connection errors in metadata_extraction.py**  
A: Verify MySQL is running and credentials in `metadata_config.yml` are correct.

**Q: PyQt5 dialogs don't appear**  
A: Ensure you have a display server running (Linux) or try running in a GUI environment.

## Credits

This project builds upon excellent open-source tools and frameworks:

- **[Keras](https://keras.io/)** - Deep learning library for image classification models
- **[TensorFlow](https://www.tensorflow.org/)** - Machine learning platform
- **[OpenNSFW2](https://github.com/bhky/opennsfw2)** - NSFW image detection model
- **[Stable Diffusion](https://stability.ai/)** - AI image generation (metadata support)
- **[Pillow](https://python-pillow.org/)** - Python Imaging Library
- **[PyQt5](https://www.riverbankcomputing.com/software/pyqt/)** - GUI framework

## License

This project is provided as-is for personal and educational use. Please refer to individual library licenses for their respective terms.

---

**Note**: This tool is designed for organizing and filtering image collections. Always respect copyright and content policies when using AI-generated images.
