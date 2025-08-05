# email-service

This project provides a standalone email service to manage email functionalities for all TeamShiksha applications. It offers flexibility, reliability, and ease of integration across multiple projects.

## Made with

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![HTML5](https://img.shields.io/badge/html5-%23E34F26.svg?style=for-the-badge&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/css3-%231572B6.svg?style=for-the-badge&logo=css3&logoColor=white)
![Code](https://img.shields.io/badge/Visual_Studio_Code-0078D4?style=for-the-badge&logo=visual%20studio%20code&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-%23FF9900.svg?style=for-the-badge&logo=amazon-aws&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/github%20actions-%232671E5.svg?style=for-the-badge&logo=githubactions&logoColor=white)
![Vercel](https://img.shields.io/badge/vercel-%23000000.svg?style=for-the-badge&logo=vercel&logoColor=white)
![Gmail](https://img.shields.io/badge/Gmail-D14836?style=for-the-badge&logo=gmail&logoColor=white)

## Set environmental variables

- Use the `.env_example` file as a reference to set up your environment variables.
- Rename it to `.env` and populate the required values.

## Run the project locally

```bash
git clone https://github.com/TeamShiksha/email-service.git
cd email-service
pip install -r requirements.txt
python run.py
```

## Access the Application

- By default, the app runs at: `http://localhost:{PORT}`, where PORT is the value you provided in the `.env` file. In case, it's not provided the app will run on PORT `8000`.
- Navigate to the `/`, `/docs`, or `/openapi.json` routes for API documentation and to explore all the available endpoints.

Click [here](./DEVELOPMENT.md) to learn how to setup your template and trigger the endpoint.

---
<p align="center" style="text"><strong>If you liked something about this repository, do give it a 🌟.</strong></p>