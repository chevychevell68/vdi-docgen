
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
{% if data.get('other_host_config') %}- **Other Host Configuration:** {{ data.get('other_host_config') }}
{% endif %}

## Storage
- **Type:** {{ data.get('storage_type','') }}
{% if data.get('storage_type') != 'vsan' %}- **Vendor:** {{ data.get('storage_vendor','') }}
- **Model:** {{ data.get('storage_model','') }}
- **Usable Capacity (TB):** {{ data.get('storage_capacity_tb','') }}
{% else %}_vSAN selected: vendor/model/capacity not required._
{% endif %}

## Networking & Load Balancing
- **Load Balancer:** {{ data.get('load_balancer','') }}

## Access & Identity
- **Integrate with 3rd‑party IdP?:** {{ data.get('idp_integrate','') }}
{% if data.get('idp_integrate') == 'yes' %}- **IdP Provider:** {{ data.get('idp_provider','') }}
{% endif %}

## Additional Notes
{{ data.get('notes','') }}

