{% extends "base.html" %}
{% block title %}Pre-Deployment Guide{% endblock %}
{% block content %}
  <h1>Pre-Deployment Guide</h1>
  <p class="text-muted">Placeholder page. Add your checklist/template when ready.</p>
  <div class="btn-group">
    <a class="btn btn-outline-primary" href="{{ url_for('index') }}">Home</a>
    <a class="btn btn-primary" href="{{ url_for('presales') }}">Go to Presales Form</a>
  </div>
{% endblock %}
