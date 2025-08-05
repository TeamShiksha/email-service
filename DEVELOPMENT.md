### Steps to Add a New Template

1. **Create the Template File**
   - Navigate to the `templates` directory
   - Create your HTML template file following the naming convention: `{project_name}/{template_name}.html`
   - Use Jinja2 syntax for dynamic variables: `{{ variable_name }}`

   Example template structure:
   ```html
   <!DOCTYPE html>
   <html>
   <head>
       <title>{{ subject }}</title>
   </head>
   <body>
       <h1>Hello {{ recipient_name }}!</h1>
       <p>{{ message_content }}</p>
   </body>
   </html>
   ```

2. **Update Template Hash Map**
   - Open `app/config.py`
   - Add your template mapping to `TEMPLATE_HASH_MAP`
   - The key should be a unique identifier, and the value should be the template file path

   ```python
   TEMPLATE_HASH_MAP = {
       "existing_template_id": "existing_project/template.html",
       "your_template_id": "your_project/your_template.html",
   }
   ```

3. **Update Schema Validation**
   - Open `app/schemas/email.py`
   - Add your template ID and required keys to the `required_keys_map` in the `check_body_for_id` method
   - The key should match your template ID, and the value should be a set of required field names

   ```python
   required_keys_map = {
       .
       .
       .
       your_template_id: {"your_required_field1", "your_required_field2"},  # Add your template validation
   }
   ```

4. **Create Email Request**
   - When sending emails via the `/email` endpoint, use your template ID in the request body:
   
   ```json
   {
       "id": your_template_id,
       "to": ["recipient@example.com"],
       "subject": "Your Subject",
       "body": {
           "your_required_field1": "Value 1",
           "your_required_field2": "Value 2"
       },
       "provider": "SES"
   }
   ```