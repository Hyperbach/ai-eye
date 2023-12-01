import logging
from http import HTTPStatus

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from openai import APIStatusError, OpenAI

logger = logging.getLogger("console")


class AssistantUploader:
    @classmethod
    def update_assistant_in_openai(cls, openai_key, openai_id, update_payload):
        logger.info("Updating assistant using OpenAI API.")

        try:
            client = OpenAI(api_key=openai_key)
            return client.beta.assistants.update(openai_id, **update_payload)
        except Exception as exc:
            logger.error(
                f"An error occurred while updating assistant in OpenAI: {str(exc)}"
            )
            raise

    @classmethod
    def create_assistant_in_openai(
        cls, openai_key, prefixed_name, uploaded_data, openai_file_ids
    ):
        logger.info("Creating assistant using OpenAI API.")

        try:
            client = OpenAI(api_key=openai_key)

            # Extracting necessary information from the assistant argument
            name = prefixed_name

            # Only retrieval is supported for now
            tools = [{"type": "retrieval"}]

            # Creating the assistant in OpenAI
            response = client.beta.assistants.create(
                instructions=uploaded_data.get("instructions", ""),
                name=name,
                tools=tools,
                model=uploaded_data.get("model", ""),
                file_ids=openai_file_ids,
            )

            logger.info(f"Received response from OpenAI API: {response}")

            return response

        except Exception:
            logger.exception("An error occurred while creating assistant in OpenAI.")
            raise


class DocumentUploader:
    @classmethod
    def delete(cls, openai_key, object_id):
        try:
            client = OpenAI(api_key=openai_key)
            return client.files.delete(object_id)
        except APIStatusError as exc:
            if exc.status_code == HTTPStatus.NOT_FOUND:
                logger.info(
                    f"File not found in OpenAI, proceeding with deletion: {exc}"
                )
            else:
                logger.error(f"Error deleting file from OpenAI: {exc}")
            raise
        except Exception as exc:
            logger.exception("General error deleting file from OpenAI")
            raise

    @classmethod
    def upload_file_to_openai(cls, openai_key, uploaded_file, user_id):
        logger.info("Starting upload to OpenAI.")

        original_file_name = uploaded_file.name
        logger.info(f"Received file: {original_file_name}")

        # Generate new filename with prefix
        prefix = f"1g_{user_id}_"
        new_file_name = prefix + original_file_name

        # Save the file with the new name
        temp_file = default_storage.save(
            new_file_name, ContentFile(uploaded_file.read())
        )
        logger.info(f"Temporary file saved: {temp_file}")

        # Upload to OpenAI with the new filename
        logger.info("Sent file to OpenAI API.")

        try:
            client = OpenAI(api_key=openai_key)
            response = client.files.create(
                file=open(temp_file, "rb"), purpose="assistants"
            )
            logger.info(f"Received response from OpenAI API: {response}")

            default_storage.delete(temp_file)
            logger.info("Temporary file deleted.")

            return response
        except Exception:
            logger.exception("An error occurred while uploading file to OpenAI.")
            default_storage.delete(temp_file)
            raise
