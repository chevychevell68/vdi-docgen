# Presales Questionnaire Export

_Exported: {{ now.strftime('%Y-%m-%d %H:%M UTC') }}_

## Voice of the Customer
{{ data.get('voc','') }}

---

## Environment & Scope
- **Deployment Scope:** {{ data.get('pod_scope','') }}
- **Include Test/Dev:** {{ data.get('include_test_dev','') }}
{% if data.get('test_dev_notes') %}- **Test/Dev Notes:** {{ data.get('test_dev_notes') }}
{% endif %}

## Host / Cluster Configuration
- **CPU per Host:** {{ data.get('cpu_per_host','') }}
- **RAM per Host:** {{ data.get('ram_per_host','') }}

## Storage
- **Type:** {{ data.get('storage_type','') }}
{% if data.get('storage_type') != 'vsan' %}- **Vendor:** {{ data.get('storage_vendor','') }}
- **Model:** {{ data.get('storage_model','') }}
{% endif %}
