web:
  user: www-data
  port: 8080
  packages:
    - nginx
    - curl
database:
  host: db.internal.example
  credentials:
    username: app_reader
    password: CHANGE_ME
