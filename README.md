# notification-service

A shared notification service for all TeamShiksha applications. Projects send a
template key and a list of recipients; the service renders the template and
delivers one message per recipient through the configured provider.

- **Channels:** email today (Amazon SES, Autosend, Gmail SMTP). The API and
  provider layer are channel-agnostic, ready for SMS, WhatsApp and push.
- **No BCC blasts:** audiences are sent as individual messages (batched
  through Autosend's bulk API where possible), which is what keeps them out of
  spam. See [docs/notification-service.md](./docs/notification-service.md).
- **Backward compatible:** existing callers of `POST /email` keep working.

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

- Use the `env_example` file as a reference to set up your environment variables.
- Only `APP_SECRET` is required; each provider is enabled when its settings are present.
- Rename it to `.env` and populate the required values.

## Run the project locally

```bash
git clone https://github.com/TeamShiksha/email-service.git
cd email-service
pip install --require-hashes --only-binary :all: -r requirements-dev.lock
python -m pytest -q
python run.py
```

## Access the Application

- By default, the app runs at: `http://localhost:{PORT}`, where PORT is the value you provided in the `.env` file. In case, it's not provided the app will run on PORT `8000`.
- Navigate to the `/`, `/docs`, or `/openapi.json` routes for API documentation and to explore all the available endpoints.

## Send a notification

```bash
curl -X POST "$URL/v1/notifications" \
  -H "Authorization: Bearer $APP_SECRET" -H "Content-Type: application/json" \
  -d '{"template":"rsvp.update","subject":"Starting soon",
       "data":{"eventName":"Meetup","updatesText":"6pm","updatesLink":"https://..."},
       "recipients":[{"to":"a@example.com"},{"to":"b@example.com"}]}'
```

`GET /v1/templates` lists every template and the data it needs.

Click [here](./DEVELOPMENT.md) to learn how to add a template.

---
<p align="center" style="text"><strong>If you liked something about this repository, do give it a 🌟.</strong></p>