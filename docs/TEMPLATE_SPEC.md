# Template build spec (Django + Skote)

You are writing Django templates for BCP Studio, which is built ON the Skote
Bootstrap admin template. USE Skote's real components (cards, `.badge`, tables,
`.btn`, modals, ApexCharts, FullCalendar, DataTables) — do NOT invent new CSS.

## The base pattern (every page)
```django
{% extends 'partials/base.html' %}
{% load static %}
{% block contents %}
   ... page body goes here, inside Bootstrap rows/cols ...
{% endblock %}
{% block extra_javascript %}
   ... optional page JS; libs live under static 'libs/...' ...
{% endblock %}
```
- `partials/base.html` already renders the sidebar, header, and a page title from
  the view's `heading`/`pageview` context. Put your body in `{% block contents %}`.
- The page is inside a Bootstrap 5 `.container-fluid`. Use `<div class="row">` /
  `<div class="col-*">` / `.card` / `.card-body`.
- Money: `{% load studio_extras %}` then `${{ some_cents|dollars }}` or `|cents`.
- Status badges: `<span class="badge bg-{{ obj.badge }}">{{ obj.get_status_display }}</span>`.
- CSRF on every POST form: `{% csrf_token %}`.
- Reference examples already written: `templates/studio/dashboard.html` and
  `templates/studio/clients_list.html` — MIRROR their style.

## ApexCharts (Skote ships it)
```django
{% block extra_javascript %}
<script src="{% static 'libs/apexcharts/dist/apexcharts.min.js' %}"></script>
<script>
  new ApexCharts(document.querySelector("#chart"),
    { chart:{type:'area',height:320,toolbar:{show:false}}, colors:['#556ee6'],
      series:[{name:'x',data: {{ series_json|safe }} }], xaxis:{categories: {{ labels_json|safe }} } }
  ).render();
</script>
{% endblock %}
```

## DataTables (for list tables — optional but nice)
CSS in `{% block extra_css %}`:
`<link href="{% static 'libs/datatables.net-bs4/css/dataTables.bootstrap4.min.css' %}" rel="stylesheet">`
JS in `{% block extra_javascript %}`:
```
<script src="{% static 'libs/datatables.net/js/jquery.dataTables.min.js' %}"></script>
<script src="{% static 'libs/datatables.net-bs4/js/dataTables.bootstrap4.min.js' %}"></script>
<script>$(function(){ $('#datatable').DataTable({pageLength:10, order:[]}); });</script>
```
Give the `<table id="datatable" class="table table-bordered dt-responsive nowrap w-100">`.

## FullCalendar (v6 global build)
CSS: none required beyond app.min.css. JS:
`<script src="{% static 'libs/fullcalendar/index.global.min.js' %}"></script>`
```
new FullCalendar.Calendar(el, { initialView:'dayGridMonth',
  headerToolbar:{left:'prev,next today',center:'title',right:'dayGridMonth,listMonth'},
  events:'/calendar/events/?scope=company' }).render();
```

## Icons
Skote bundles Boxicons (`bx bx-*`, brand icons `bx bxl-instagram` etc.) and
Material Design Icons (`mdi mdi-*`). Use Boxicons.
