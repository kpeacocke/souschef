# Deliberately malformed YAML indentation in a state argument list.
nginx:
  pkg.installed:
    - name: nginx
      - require:
      - service: nginx
