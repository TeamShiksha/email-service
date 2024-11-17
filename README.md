# email-service

**Independent Email Service for all TeamShiksha Projects**

This project provides a standalone email service to manage email functionalities for all TeamShiksha applications. It offers flexibility, reliability, and ease of integration across multiple projects.

---

## How to Run the Project

1. **Clone the Repository**:
    ```bash
    git clone https://github.com/TeamShiksha/email-service.git
    cd email-service
    ```

2. **Set up a Virtual Environment**:
    ```bash
    python -m venv venv
    ```

3. **Activate the Virtual Environment**:
    - **Windows**:
        ```bash
        venv\Scripts\activate
        ```
    - **Mac/Linux**:
        ```bash
        source venv/bin/activate
        ```

4. **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

5. **Configure Environment Variables**:
    - Use the `.env_example` file as a reference to set up your environment variables.
    - Rename it to `.env` and populate the required values.

6. **Run the Application**:
    ```bash
    python run.py
    ```

---

## Development Mode with Auto-Reload

To enable development mode with live reload, use the following command:
```bash
uvicorn app.main:app --env-file=.env --reload
```


## Access the Application

- By default, the app runs at: http://localhost:8000
- Navigate to the `/docs` route for API documentation and to explore all the available endpoints.