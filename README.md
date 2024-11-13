# Curso de LangChain para Manejo y Recuperación de Documentos

## Clonación del repositorio

```bash
git clone https://github.com/platzi/curso-langchain-qa-documents.git
```

## Configuración de una sola vez

- Instalación de [pyenv](https://github.com/pyenv/pyenv).

- Instalación de Python con:

```bash
pyenv install 3.11.2
```

- Activación de Python con:

```bash
pyenv local 3.11.2
```

- Instalación de [Poetry](https://python-poetry.org/docs/#installation).

- Configuración de Poetry para crear ambientes virtuales dentro de la raíz del proyecto con:

```bash
poetry config virtualenvs.in-project true
```

- Instalación de dependencias con:

```bash
poetry install
```

- Activación del ambiente virtual con:

```bash
poetry shell
```

## Ejecución de la aplicación

- Obtención de las variables de entorno:

    - `OPENAI_API_KEY`: API Key de OpenAI.

- Inicialización de la aplicación con:

    ```bash
    streamlit run app.py
    ```

    o
        
    ```bash
    poetry run streamlit run app.py
    ```
