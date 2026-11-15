{% set web_user = pillar.get('web:user', 'www-data') %}
{% set web_port = pillar.get('web:port', 8080) %}

nginx_repository:
  pkgrepo.managed:
    - name: deb http://deb.debian.org/debian stable main

nginx_package:
  pkg.installed:
    - name: nginx
    - require:
      - pkgrepo: nginx_repository

/etc/nginx/sites-available/example:
  file.managed:
    - source: salt://templates/example.conf
    - template: jinja
    - user: {{ web_user }}
    - mode: '0640'
    - require:
      - pkg: nginx_package

nginx_service:
  service.running:
    - name: nginx
    - enable: true
    - watch:
      - file: /etc/nginx/sites-available/example
