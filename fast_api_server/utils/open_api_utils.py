from fastapi.openapi.utils import get_openapi

def customise_open_api(app):
    DESC = """
API for storing and managing student progress with PythonSponge.

This current schema emerged as a result of continuous tweaks while using PythonSponge in a secondary school.

Authentication is based on JWT bearer tokens, with a single endpoint to acquire the token. Access control is two-tiered: students and teachers. Students only see books available to them and their own results. Teachers are effectively superusers. Most parts of the API are inspired by REST, but don't follow it strictly.

**Key entities in the API:**

- **Student**: A student is identified by their student ID. We've found it best to use the first part of the student email. Students are keyed with this student ID, and the server provides a mapping to human-readable names (if available) while resolving results.

- **Book**: A book is a set of challenges. Books are identified by a URL path (e.g., `/books/unit1/book.json`). Books have a title that the server needs to extract when displaying the student dashboard.

- **Challenge**: A single challenge within a book. Challenges are identified by a UUID.

- **Class**: A collection of students and books. Classes are identified by a name and contain lists of students, books, and optionally disabled books.

> Note: In this API, student codes are checked purely client-side. If the server has reason to distrust a result, it can re-run checks on the submitted code.
"""

    
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title="PythonSponge API",
            version="0.9.1",
            description=DESC,
            routes=app.routes,
        )

        # Add extra metadata
        openapi_schema["info"]["contact"] = {
            "email": "gdenes355@gmail.com",
            "url": "https://www.pythonsponge.com/",
        }

        openapi_schema["info"]["license"] = {
            "name": "MIT",
            "url": "https://opensource.org/license/mit/",
        }

        openapi_schema["info"]["x-logo"] = {
            "url": "https://raw.githubusercontent.com/gdenes355/python-frontend/b9777bf5974b6d38cc8f25bf652794cf326d5958/public/logo40.png",
            "altText": "PythonSponge logo",
        }

        # Inject x-badges into admin endpoints
        teacher_badge = {"name": "Teacher", "color": "purple", "position": "after"}
        

        for path in openapi_schema["paths"]:
            if 'admin' in path:
                for method in openapi_schema["paths"][path]:
                    openapi_schema["paths"][path][method]["x-badges"] = [teacher_badge]

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi