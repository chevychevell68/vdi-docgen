
# Pre-Deployment Checklist
_Generated: {{ now.strftime('%Y-%m-%d %H:%M UTC') }}_

## Global
{% for f in fields if f.applies_to|lower in ["global","both"] -%}
- [ ] {{ f.label }} {% if f.required|lower in ["yes","true","1"] %}**(Required)**{% endif %}
{% endfor %}

## Pod 1
{% for f in fields if f.applies_to|lower in ["pod1","both"] -%}
- [ ] {{ f.label }} {% if f.required|lower in ["yes","true","1"] %}**(Required)**{% endif %}
{% endfor %}

{% if is_multi %}
## Pod 2
{% for f in fields if f.applies_to|lower in ["pod2","both"] -%}
- [ ] {{ f.label }} {% if f.required|lower in ["yes","true","1"] %}**(Required)**{% endif %}
{% endfor %}

## GSLB (Multi-Pod)
- [ ] Enable GSLB? (Yes/No)
- [ ] GSLB FQDN(s) for Horizon (Internal/External URLs)
- [ ] GTM configuration (data centers, pools, monitors)
- [ ] LTM VIPs per site (UAG, Connection Server, Admin, App Volumes, DEM)
- [ ] Health monitors (types, intervals, response codes)
- [ ] Failover/steering policy (round-robin, topology, latency, geo)
- [ ] Certificates & SNI (SANs/wildcards, renewal ownership)
{% endif %}
