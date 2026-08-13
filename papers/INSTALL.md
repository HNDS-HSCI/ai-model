# Installation & Setup Guide for HSCI Publication Package

## Prerequisites
* **Python**: Version 3.13.1 or higher
* **Git**: Any modern version
* **Graphviz / LaTeX (Optional for compilation)**: `pdflatex`, `bibtex`, `tikz`

---

## Quick Start Installation

```bash
# 1. Clone Repository
git clone https://github.com/hsci/hsci-core.git
cd hsci-core

# 2. Create Virtual Environment
python -m venv venv
# On Linux/macOS:
source venv/bin/activate
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1

# 3. Install Dependencies
pip install --upgrade pip
pip install -r requirements.txt
```
