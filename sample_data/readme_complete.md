# ProjectAlpha — Open-Source ML Framework

## Overview

ProjectAlpha is an open-source machine learning framework designed for rapid prototyping and production deployment of deep learning models. It supports PyTorch and TensorFlow backends.

## Installation

```bash
pip install projectalpha
```

Requirements:
- Python 3.9+
- CUDA 11.8+ (for GPU support)

## Quick Start

```python
import projectalpha as pa

model = pa.Model("resnet50", pretrained=True)
result = model.predict(image)
```

## API Reference

### `pa.Model(name, pretrained=False)`

Creates a model instance.

**Parameters:**
- `name` (str): Model architecture name
- `pretrained` (bool): Whether to load pretrained weights

**Returns:** Model instance

### `pa.Dataset(path, transform=None)`

Loads a dataset from disk.

**Parameters:**
- `path` (str): Path to dataset directory
- `transform` (callable): Optional data transformation pipeline

## Configuration

ProjectAlpha can be configured via `config.yaml`:

```yaml
training:
  batch_size: 32
  learning_rate: 0.001
  epochs: 100
compute:
  device: auto
  precision: fp16
```

## Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Write tests for your changes
4. Submit a pull request

### Code Style
We use `black` for formatting and `ruff` for linting.

## Testing

Run the test suite:

```bash
pytest tests/ -v
```

## License

MIT License. See [LICENSE](LICENSE) for details.

## Security Policy

### Reporting Vulnerabilities

If you discover a security vulnerability, please email security@projectalpha.dev. Do NOT open a public issue.

### Supported Versions

| Version | Supported |
|---------|-----------|
| 2.x     | ✅        |
| 1.x     | ❌        |

## Changelog

### v2.1.0 (2025-01-15)
- Added TensorFlow backend support
- Improved GPU memory management

### v2.0.0 (2024-06-01)
- Major API redesign
- Breaking changes from 1.x
