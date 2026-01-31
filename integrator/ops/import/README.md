# Domain Data Import/Export System

This directory contains the import functionality for domain-related data, which works in conjunction with the export functionality in `ops/export/`.

## Overview

The domain data consists of five main tables:
- **categories**: Dynamic, hierarchical categories for organizing capabilities
- **capabilities**: Canonical capabilities with descriptions and constraints
- **operations**: Individual operations with input/output specifications
- **category_capability**: Relationships between categories and capabilities
- **capability_operation**: Relationships between capabilities and operations

## Files

### `00_domain_import.py`
Main import script that can restore domain data from JSON backups created by the export system.

**Features:**
- Complete metadata restoration including IDs, timestamps, and embeddings
- Support for both merge mode (preserve existing data) and replace mode (clear existing data)
- Automatic dependency handling (imports in correct order)
- Comprehensive error handling and logging
- Auto-detection of most recent backup if no specific backup specified

**Usage:**
```bash
# Import from most recent backup (merge mode)
python 00_domain_import.py backup_data/domain_bk/domains

```


# tenant Data Import/Export System

**Usage:**
```bash
#  from most recent backup (merge mode)
python 01_tenant_import.py backup_data/tenant_bk

```


# iam Data Import/Export System

**Usage:**
```bash
# Import from most recent backup (merge mode)
python 01_tenant_import.py backup_data/tenant_bk

```




# iam Data Import/Export System

**Usage:**
```bash
# Import from most recent backup (merge mode)
 python 02_iam_import.py backup_data/iam_bk


```
