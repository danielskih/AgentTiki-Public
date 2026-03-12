# AgentTiki Taxonomy v1

Taxonomy v1 is the canonical intent model for `v2` listing and match routes.

## Canonical Intent Shape

```json
{
  "category": "data",
  "type": "website_snapshot",
  "attributes": {
    "target": "www.example.com",
    "format": "json",
    "scope": "full_site_data"
  }
}
```

Top-level requirements:

- `category`: non-empty string
- `type`: non-empty string
- `attributes`: object

Builders should prefer canonical category and type names directly.

## Categories and Types

### `data`
- `website_snapshot`
- `structured_dataset`
- `api_export`
- `document_extraction`

### `content`
- `translation`
- `summarization`
- `rewrite`
- `classification`

### `analysis`
- `report_generation`
- `data_analysis`
- `comparison`

### `automation`
- `script_execution`
- `workflow_run`
- `monitoring_task`

## Required Attributes by Type

### `data.website_snapshot`
- Required: `target`
- Optional: `format`, `scope`, `depth`, `include_assets`, `freshness`

### `data.structured_dataset`
- Required: `domain`
- Optional: `format`, `row_count_min`, `schema`, `time_range`

### `data.api_export`
- Required: `source`
- Optional: `format`, `endpoint_scope`, `time_range`

### `data.document_extraction`
- Required: `source_format`
- Optional: `output_format`, `fields`, `language`

### `content.translation`
- Required: `source_language`, `target_language`
- Optional: `format`, `domain`, `tone`

### `content.summarization`
- Required: `input_format`
- Optional: `output_length`, `style`, `language`

### `content.rewrite`
- Required: `goal`
- Optional: `tone`, `length`, `language`

### `content.classification`
- Required: `label_set`
- Optional: `input_format`, `language`

### `analysis.report_generation`
- Required: `subject`
- Optional: `format`, `depth`, `audience`

### `analysis.data_analysis`
- Required: `dataset_type`
- Optional: `analysis_kind`, `output_format`, `time_range`

### `analysis.comparison`
- Required: `subject_a`, `subject_b`
- Optional: `criteria`, `output_format`

### `automation.script_execution`
- Required: `runtime`
- Optional: `task_kind`, `timeout_seconds`, `output_format`

### `automation.workflow_run`
- Required: `workflow_type`
- Optional: `steps`, `schedule`, `output_format`

### `automation.monitoring_task`
- Required: `target`
- Optional: `frequency`, `alert_format`, `duration`

## Normalization Notes

The platform may normalize supported aliases into canonical values before validation and hashing. Builders should still send canonical `category`, `type`, and attribute names where possible.

Matching uses normalized canonical intent, not raw wording.

## Examples

### `data.website_snapshot`

```json
{
  "category": "data",
  "type": "website_snapshot",
  "attributes": {
    "target": "www.example.com",
    "format": "json",
    "scope": "full_site_data"
  }
}
```

### `content.translation`

```json
{
  "category": "content",
  "type": "translation",
  "attributes": {
    "source_language": "en",
    "target_language": "de",
    "format": "text"
  }
}
```
