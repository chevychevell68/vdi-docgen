# Presales Questionnaire Export

_Exported: {{ now.strftime('%Y-%m-%d %H:%M UTC') }}_

## Customer & Project
- **Customer Name:** {{ data.get('customer_name','') }}
- **Customer Slug:** {{ data.get('customer_slug','') }}
- **Project Name:** {{ data.get('project_name','') }}

## Primary Contacts
- **Primary Contact (Name):** {{ data.get('primary_contact_name','') }}
- **Primary Contact (Email):** {{ data.get('primary_contact_email','') }}
{% if data.get('secondary_contacts') %}- **Secondary / Ops Contacts:** {{ data.get('secondary_contacts','') }}{% endif %}

## Voice of the Customer
{{ data.get('voc','') }}

## Scope
- **Deployment Scope:** {{ data.get('pod_scope','') }}
- **Include Test/Dev:** {{ data.get('include_test_dev','') }}
- **Concurrent Users:** {{ data.get('concurrent_users','') }}
{% if data.get('test_dev_notes') %}- **Test/Dev Notes:** {{ data.get('test_dev_notes','') }}{% endif %}

## Host / Cluster Sizing
- **ESXi Hosts (per pod):** {{ data.get('host_count','') }}
- **CPU per Host:** {{ data.get('cpu_per_host','') }}
- **RAM per Host:** {{ data.get('ram_per_host','') }}
{% if data.get('other_host_config') %}- **Other Host Details:** {{ data.get('other_host_config','') }}{% endif %}

## Storage
- **Type:** {{ data.get('storage_type','') }}
{% if data.get('storage_type') != 'vSAN' %}- **Vendor:** {{ data.get('storage_vendor','') }}
- **Model:** {{ data.get('storage_model','') }}
- **Usable Capacity (TB):** {{ data.get('storage_capacity_tb','') }}{% endif %}

## Networking & Load Balancing
- **Load Balancer:** {{ data.get('load_balancer','') }}
- **Management Network CIDR:** {{ data.get('mgmt_cidr','') }}
- **VM / Desktop Networks:** {{ data.get('vm_networks','') }}

## Access & Identity
- **Integrate with 3rd-party IdP?:** {{ data.get('idp_integrate','') }}
{% if data.get('idp_integrate') == 'yes' %}- **IdP Provider:** {{ data.get('idp_provider','') }}{% endif %}

## Additional Notes
{{ data.get('notes','') }}
