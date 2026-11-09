# Diseño de infraestructura de red

Integrantes del grupo:

* Mateo Delmagro
* Benicio Sánchez Mandato

# Tutorial de Ejecución local

Ambos proyectos tienen definido este target:

```
make clean
```

## Back end

En la carpeta `backend/` instalá el entorno una sola vez:

```
make venv
```

Luego correlo localmente:

```
make release
```

Corré los tests:

```
make tests
```

## Front end

En la carpeta `frontend/` corré la página localmente (require Elm y `http.server` en Python)
```
make release
```
