# BetaLib — Data Processing Library

## Overview

BetaLib is a data processing library for ETL pipelines. It handles CSV, JSON, and Parquet formats with built-in validation.

## Installation

```bash
pip install betalib
```

## Quick Start

```python
import betalib

pipeline = betalib.Pipeline("input.csv")
pipeline.transform(clean=True)
pipeline.save("output.parquet")
```

## API Reference

### `betalib.Pipeline(source)`

Creates a processing pipeline.

**Parameters:**
- `source` (str): Path to input file

## Configuration

Set options via environment variables:

```bash
export BETALIB_WORKERS=4
export BETALIB_CACHE_DIR=/tmp/betalib
```

## Changelog

### v1.2.0
- Added Parquet support
- Fixed memory leak in CSV parser
