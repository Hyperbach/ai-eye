import datetime
import logging
from http import HTTPStatus

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View, generic
from django.views.generic import TemplateView

from api.models import Log
from api.permissions import AiEyeAdminPermission
from api.serializers import AssistantSerializer, DocumentSerializer
from core.forms import UserCreateForm
from core.mixins import AiEyeAdminMixin, AiEyeAdminOrUserMixin
from core.models import APIKey, PublicToken
from core.services.uploaders import AssistantUploader, DocumentUploader
from dashboard.forms import PublicTokenCreateForm, PublicTokenUpdateForm
from dashboard.serializers import BuiltinFunctionsSyncSerializer
from dblogs.models import PipelineExecutionLog
from openai import APIStatusError, OpenAI
from pipelines.forms import AssistantForm, DocumentForm, PipelineCreateForm
from pipelines.models import (
    Assistant,
    BuiltinFunction,
    Document,
    PipelineSource,
    Prompt,
)
from pipelines.services.functions_manager import FUNCTIONS_MANAGER
from rest_framework import permissions, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger("console")

User = get_user_model()


class UserCreateView(AiEyeAdminMixin, generic.CreateView):
    template_name = "dashboard/users/create.html"
    form_class = UserCreateForm
    success_url = reverse_lazy("dashboard:users")


class UserListView(AiEyeAdminMixin, generic.ListView):
    template_name = "dashboard/users/list.html"

    def get_queryset(self):
        return User.aieye_users_objects.order_by("-date_created")


class OpenAIKeysBaseView(AiEyeAdminMixin, View):
    success_url = reverse_lazy("dashboard:openaikeys")

    def get_queryset(self):
        return APIKey.objects.filter(owner=self.request.user).order_by(
            "-date_created"
        )


class OpenAIKeysListView(OpenAIKeysBaseView, generic.ListView):
    fields = "__all__"
    template_name = "dashboard/openaikeys/list.html"


class OpenAIKeysCreateView(OpenAIKeysBaseView, generic.CreateView):
    fields = ["key"]
    template_name = "dashboard/openaikeys/create.html"

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.owner = self.request.user
        return super().form_valid(form)


class OpenAIKeysUpdateView(OpenAIKeysBaseView, generic.UpdateView):
    fields = ["key", "is_active"]
    template_name = "dashboard/openaikeys/update.html"


class OpenAIKeysDeleteView(OpenAIKeysBaseView, generic.DeleteView):  # type: ignore[misc]
    template_name = "dashboard/openaikeys/delete.html"


class PublicTokensFormMixin:
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["apikey"].queryset = APIKey.objects.filter(
            owner=self.request.user
        )
        form.fields["user"].queryset = User.aieye_users_objects
        return form


class PublicTokensBaseViewMixin(AiEyeAdminMixin):
    success_url = reverse_lazy("dashboard:publictokens")

    def get_queryset(self):
        return (
            PublicToken.objects.filter(apikey__owner=self.request.user)
            .prefetch_related("user", "apikey")
            .order_by("-date_created")
        )


class PublicTokensListView(PublicTokensBaseViewMixin, generic.ListView):
    fields = "__all__"
    template_name = "dashboard/publictokens/list.html"


class PublicTokensCreateView(
    PublicTokensFormMixin, PublicTokensBaseViewMixin, generic.CreateView
):
    template_name = "dashboard/publictokens/create.html"
    form_class = PublicTokenCreateForm


class PublicTokensUpdateView(
    PublicTokensFormMixin, PublicTokensBaseViewMixin, generic.UpdateView
):
    template_name = "dashboard/publictokens/update.html"
    form_class = PublicTokenUpdateForm


class PublicTokensDeleteView(PublicTokensBaseViewMixin, generic.DeleteView):  # type: ignore[misc]
    template_name = "dashboard/publictokens/delete.html"


class CachesBaseViewMixin(AiEyeAdminMixin):
    success_url = reverse_lazy("dashboard:caches")

    def get_queryset(self):
        return Log.objects.prefetch_related("user", "api_key").order_by("-timestamp")


class CachesListView(CachesBaseViewMixin, generic.ListView):
    fields = "__all__"
    template_name = "dashboard/caches/list.html"
    paginate_by = 100


class CachesDeleteView(CachesBaseViewMixin, generic.DeleteView):  # type: ignore[misc]
    template_name = "dashboard/caches/delete.html"


class CachesDeleteAllView(AiEyeAdminMixin, generic.FormView):
    template_name = "dashboard/caches/delete_all.html"
    success_url = reverse_lazy("dashboard:caches")

    form_class = forms.Form

    def form_valid(self, form):
        Log.objects.all().delete()
        return super().form_valid(form)


class PromptBaseView(AiEyeAdminOrUserMixin, View):
    success_url = reverse_lazy("dashboard:prompts")

    def get_queryset(self):
        user = self.request.user
        qs = Prompt.objects
        if user.is_aieye_user:
            qs = qs.filter(owner=user)

        return qs.order_by("-date_created")


class PromptListView(PromptBaseView, generic.ListView):
    fields = "__all__"
    template_name = "dashboard/prompts/list.html"


class PromptCreateView(PromptBaseView, generic.CreateView):
    fields = ["name", "body", "description", "type"]
    template_name = "dashboard/prompts/create.html"

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.owner = self.request.user
        return super().form_valid(form)


class PromptDeleteView(PromptBaseView, generic.DeleteView):  # type: ignore[misc]
    template_name = "dashboard/prompts/delete.html"


class PromptUpdateView(PromptBaseView, generic.UpdateView):
    fields = ["name", "body", "description", "type"]
    template_name = "dashboard/prompts/update.html"


class BuiltinFunctionBaseView(AiEyeAdminMixin, View):
    success_url = reverse_lazy("dashboard:builtins")

    def get_queryset(self):
        return BuiltinFunction.objects.order_by("-date_created")


class BuiltinFunctionListView(AiEyeAdminOrUserMixin, generic.ListView):
    fields = "__all__"
    template_name = "dashboard/builtins/list.html"

    def get_queryset(self):
        return BuiltinFunction.objects.order_by("-date_created")


class SyncBuiltinFunctionsAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated, AiEyeAdminPermission)
    authentication_classes = (SessionAuthentication,)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        FUNCTIONS_MANAGER.force_reload()
        func_names = FUNCTIONS_MANAGER.get_func_names()

        funcs_to_delete_qs = BuiltinFunction.objects.exclude(name__in=func_names)
        deleted_function_names = list(funcs_to_delete_qs.values_list("name", flat=True))
        funcs_to_delete_qs.delete()

        existing_func_names = BuiltinFunction.objects.values_list("name", flat=True)
        missed_funcs = [
            BuiltinFunction(name=name, description="")
            for name in func_names
            if name not in existing_func_names
        ]
        if missed_funcs:
            BuiltinFunction.objects.bulk_create(missed_funcs)

        created_func_names = [func.name for func in missed_funcs]

        serializer = BuiltinFunctionsSyncSerializer(
            data={
                "success": True,
                "deleted": deleted_function_names,
                "created": created_func_names,
            }
        )

        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BuiltinFunctionUpdateView(BuiltinFunctionBaseView, generic.UpdateView):
    fields = ["description"]
    template_name = "dashboard/builtins/update.html"


class PipelineSourceBaseView(AiEyeAdminOrUserMixin, View):
    success_url = reverse_lazy("dashboard:pipelines")

    def get_queryset(self):
        user = self.request.user
        qs = PipelineSource.objects
        if user.is_aieye_user:
            qs = qs.filter(owner=user)

        return qs.order_by("-date_created")


class PipelineSourceListView(PipelineSourceBaseView, generic.ListView):
    fields = "__all__"
    template_name = "dashboard/pipelines/list.html"


class PipelineExecutionHistoryView(AiEyeAdminOrUserMixin, generic.ListView):
    fields = "__all__"
    template_name = "dashboard/pipelines/execution_history.html"
    paginate_by = 10

    def get_queryset(self):
        return (
            PipelineExecutionLog.objects.filter(user=self.request.user)
            .select_related("pipeline")
            .order_by("-start_date")
        )

    def get_context_data(self, *args, **kwargs):
        data = super().get_context_data(*args, **kwargs)

        # Pagination logic
        paginator = data["paginator"]
        page_obj = data["page_obj"]
        current_index = paginator.page_range.index(page_obj.number)
        max_index = len(paginator.page_range)
        start_index = current_index - 2 if current_index >= 2 else 0
        end_index = current_index + 3 if current_index <= max_index - 3 else max_index
        data["page_range"] = paginator.page_range[start_index:end_index]

        # Calculate execution time for each log entry
        for log in page_obj:
            if log.start_date and log.end_date:
                duration = (log.end_date - log.start_date).total_seconds() * 1000
                log.execution_time_ms = int(duration)
            else:
                log.execution_time_ms = None

        return data


class PipelineDetailExecHistoryView(PipelineExecutionHistoryView):
    def get_queryset(self):
        return super().get_queryset().filter(pipeline_id=self.kwargs["pk"])

    def get_context_data(self, *args, **kwargs):
        data = super().get_context_data(*args, **kwargs)
        filter_kwargs = {
            "pk": self.kwargs["pk"],
        }
        if not self.request.user.is_aieye_admin:
            filter_kwargs.update(owner=self.request.user)

        pipeline = get_object_or_404(PipelineSource, **filter_kwargs)
        data["pipeline"] = pipeline

        return data


class PipelineSourceCreateView(PipelineSourceBaseView, generic.CreateView):
    template_name = "dashboard/pipelines/create.html"
    form_class = PipelineCreateForm
    success_url = reverse_lazy("dashboard:pipelines")

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.owner = self.request.user
        return super().form_valid(form)


class PipelineSourceUpdateView(PipelineSourceBaseView, generic.UpdateView):
    form_class = PipelineCreateForm
    template_name = "dashboard/pipelines/update.html"


class PipelineSourceDeleteView(PipelineSourceBaseView, generic.DeleteView):  # type: ignore[misc]
    template_name = "dashboard/pipelines/delete.html"


class PipelineSourceExecuteView(AiEyeAdminOrUserMixin, TemplateView):
    template_name = "dashboard/pipelines/execute.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        qs = PipelineSource.objects
        if user.is_aieye_user:
            qs = qs.filter(owner=user)

        pipelines = qs.order_by("-date_created")
        openaikeys = (
            APIKey.objects.filter(
                Q(owner=user) | Q(users__in=[user]), is_active=True
            )
            .distinct()
            .order_by("-date_created")
        )

        context.update({"pipelines": pipelines, "openaikeys": openaikeys})
        if selected_pipeline := kwargs.get("id"):
            context.update({"selected_pipeline": selected_pipeline})

        return context


def index(request):
    if request.user.is_authenticated:
        if request.user.is_aieye_admin:
            return redirect("dashboard:users")
        else:
            return redirect("dashboard:prompts")
    else:
        return redirect("access:login")


class DocumentBaseView(AiEyeAdminOrUserMixin, View):
    success_url = reverse_lazy("dashboard:document_list")
    serializer_class = DocumentSerializer

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        openaikeys = (
            APIKey.objects.filter(
                Q(owner=user) | Q(users__in=[user]), is_active=True
            )
            .distinct()
            .order_by("-date_created")
        )

        context.update({"openaikeys": openaikeys})

        return context

    def get_queryset(self):
        user = self.request.user
        qs = Document.objects
        if user.is_aieye_user:
            qs = qs.filter(owner=user)  # Assuming each document has an 'owner' field.
        return qs.order_by("-created_at")


class DocumentListView(DocumentBaseView, generic.ListView):
    template_name = "dashboard/documents/list.html"
    context_object_name = (
        "documents"  # This is used in the template to loop over the documents.
    )


class DocumentCreateView(DocumentBaseView, generic.CreateView):
    model = Document
    form_class = DocumentForm
    template_name = "dashboard/documents/create.html"
    success_url = reverse_lazy("dashboard:document_list")

    def form_valid(self, form):
        logger.info("Processing form submission.")

        try:
            api_key_id = self.request.POST.get("apikey")
            api_key = APIKey.objects.get(id=api_key_id).key

            uploaded_file = self.request.FILES["file"]
            original_file_name = uploaded_file.name
            logger.info(f"Received file: {original_file_name}")
        except Exception as exc:
            logger.error(f"An error occurred during form processing: {str(exc)}")
            form.add_error(None, f"An error occurred: {str(exc)}")
            return self.form_invalid(form)

        try:
            response = DocumentUploader.upload_file_to_openai(
                openai_key=api_key,
                uploaded_file=uploaded_file,
                user_id=self.request.user.id,
            )

            logger.info("Sent file to OpenAI API.")
            logger.debug(f"Response data from OpenAI API: {response}")

            self.object = form.save(commit=False)
            self.object.id = response.id
            self.object.object_type = response.object
            self.object.bytes = response.bytes
            self.object.filename = response.filename
            self.object.original_filename = original_file_name
            self.object.purpose = response.purpose
            self.object.created_at = datetime.datetime.fromtimestamp(
                response.created_at
            )
            logger.debug("Request user: " + str(self.request.user))
            self.object.owner = self.request.user
            self.object.save()
            logger.info(f"Document object saved with ID: {self.object.id}")

        except Exception as exc:
            logger.error(f"An error occurred during form processing: {str(exc)}")
            form.add_error(None, f"An error occurred: {str(exc)}")
            return self.form_invalid(form)

        logger.info("Form processed successfully.")
        response = super().form_valid(form)

        return response

    def get_success_url(self):
        # Override the success URL after the object is created
        if self.object:
            return reverse("dashboard:document_detail", kwargs={"pk": self.object.pk})
        else:
            return super().get_success_url()


class DocumentDetailView(DocumentBaseView, generic.DetailView):
    model = Document
    template_name = "dashboard/documents/details.html"
    context_object_name = "document"

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.is_aieye_user:
            qs = qs.filter(owner=user)
        return qs


class DocumentDeleteView(DocumentBaseView, generic.DeleteView):
    template_name = "dashboard/documents/delete.html"

    def form_valid(self, form):
        self.object = self.get_object()

        try:
            api_key_id = self.request.POST.get("apikey")
            api_key = APIKey.objects.get(id=api_key_id).key

            response = DocumentUploader.delete(
                openai_key=api_key, object_id=self.object.id
            )

            if response.deleted:
                messages.success(
                    self.request,
                    "Document and corresponding file deleted successfully.",
                )
            else:
                messages.error(self.request, "Failed to delete the file from OpenAI.")
        except APIStatusError as exc:
            if exc.status_code == HTTPStatus.NOT_FOUND:
                logger.info(
                    f"File not found in OpenAI, proceeding with deletion: {exc}"
                )
                messages.warning(
                    self.request,
                    "File not found in OpenAI, but document will be deleted from database.",
                )
            else:
                logger.error(f"Error deleting file from OpenAI: {exc}")
                messages.error(
                    self.request,
                    "An error occurred while deleting the file: {}".format(exc),
                )
                return redirect(self.success_url)
        except Exception as exc:
            logger.error(f"General error deleting file from OpenAI: {exc}")
            messages.error(self.request, "An unexpected error occurred: {}".format(exc))
            return redirect(self.success_url)

        return super().form_valid(form)

    def get(self, request, *args, **kwargs):
        """Ensure that the delete view only works with POST requests"""
        return self.post(request, *args, **kwargs)


class DocumentUpdateView(DocumentBaseView, generic.UpdateView):
    fields = ["description"]
    template_name = "dashboard/documents/update.html"


class AssistantBaseView(AiEyeAdminOrUserMixin, View):
    success_url = reverse_lazy("dashboard:assistant_list")
    serializer_class = AssistantSerializer

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        openaikeys = (
            APIKey.objects.filter(
                Q(owner=user) | Q(users__in=[user]), is_active=True
            )
            .distinct()
            .order_by("-date_created")
        )

        context.update({"openaikeys": openaikeys})

        return context

    def get_queryset(self):
        user = self.request.user
        qs = Assistant.objects
        if user.is_aieye_user:
            qs = qs.filter(owner=user)
        return qs.order_by("-created_at")


class AssistantListView(AssistantBaseView, generic.ListView):
    template_name = "dashboard/assistants/list.html"
    context_object_name = "assistants"


class AssistantCreateView(AssistantBaseView, generic.CreateView):
    model = Assistant
    form_class = AssistantForm
    template_name = "dashboard/assistants/create.html"
    success_url = reverse_lazy("dashboard:assistant_list")

    def form_valid(self, form):
        logger.info("Processing form submission.")

        try:
            logger.info("Form data: " + str(self.request.POST))

            api_key_id = self.request.POST.get("apikey")
            api_key = APIKey.objects.get(id=api_key_id).key

            cleaned_data = form.cleaned_data
            unprefixed_name = cleaned_data.get("name", "")

            # Generate new assistant name with prefix
            prefix = f"1g_{self.request.user.id}_"
            prefixed_name = prefix + unprefixed_name

            openai_file_ids = self.request.POST.getlist("files")
            logger.info(f"OpenAI file IDs: {openai_file_ids}")

            # Create assistant in OpenAI
            response = AssistantUploader.create_assistant_in_openai(
                openai_key=api_key,
                prefixed_name=prefixed_name,
                uploaded_data=cleaned_data,
                openai_file_ids=openai_file_ids,
            )

            logger.info("Created assistant in OpenAI.")
            logger.debug(f"Response data from OpenAI API: {response}")

            # Create an instance of the Assistant model with data from the form
            self.object = form.save(commit=False)
            self.object.openai_id = response.id
            self.object.prefixed_name = prefixed_name
            self.object.created_at = datetime.datetime.fromtimestamp(
                response.created_at
            )
            self.object.owner = self.request.user
            self.object.save()

            # Handling file associations
            if openai_file_ids:
                for openai_file_id in openai_file_ids:
                    try:
                        # Assuming Document model uses openai_file_id as a reference to OpenAI's file ID
                        document = Document.objects.get(id=openai_file_id)
                        self.object.files.add(document)
                    except Document.DoesNotExist:
                        logger.error(
                            f"Document with OpenAI file ID {openai_file_id} does not exist in the database."
                        )

            logger.info(f"Assistant object saved with ID: {self.object.id}")

        except Exception as exc:
            logger.error(f"An error occurred during form processing: {str(exc)}")
            form.add_error(None, f"An error occurred: {str(exc)}")
            return self.form_invalid(form)

        logger.info("Form processed successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        # Override the success URL after the object is created
        if self.object:
            return reverse("dashboard:assistant_detail", kwargs={"pk": self.object.pk})
        else:
            return super().get_success_url()


class AssistantDetailView(AssistantBaseView, generic.DetailView):
    model = Document
    template_name = "dashboard/assistants/details.html"
    context_object_name = "assistant"

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.is_aieye_user:
            qs = qs.filter(owner=user)
        return qs


class AssistantDeleteView(AssistantBaseView, generic.DeleteView):
    template_name = "dashboard/assistants/delete.html"

    def form_valid(self, form):
        self.object = self.get_object()

        try:
            api_key_id = self.request.POST.get("apikey")
            api_key = APIKey.objects.get(id=api_key_id).key

            client = OpenAI(api_key=api_key)

            response = client.beta.assistants.delete(self.object.openai_id)

            if response.deleted:
                messages.success(self.request, "Assistant deleted successfully.")
            else:
                messages.error(
                    self.request, "Failed to delete the assistant from OpenAI."
                )
        except APIStatusError as exc:
            if exc.status_code == HTTPStatus.NOT_FOUND:
                logger.info(
                    f"Assistant not found in OpenAI, proceeding with deletion: {exc}"
                )
                messages.warning(
                    self.request,
                    "Assistant not found in OpenAI, but it will be deleted from database.",
                )
            else:
                logger.error(f"Error deleting assistant from OpenAI: {exc}")
                messages.error(
                    self.request,
                    "An error occurred while deleting the assistant: {}".format(exc),
                )
                return redirect(self.success_url)
        except Exception as exc:
            logger.error(f"General error deleting assistant from OpenAI: {exc}")
            messages.error(self.request, "An unexpected error occurred: {}".format(exc))
            return redirect(self.success_url)

        return super().form_valid(form)

    def get(self, request, *args, **kwargs):
        """Ensure that the delete view only works with POST requests"""
        return self.post(request, *args, **kwargs)


class AssistantUpdateView(AssistantBaseView, generic.UpdateView):
    model = Assistant
    form_class = AssistantForm
    template_name = "dashboard/assistants/update.html"
    success_url = reverse_lazy("dashboard:assistant_list")

    def form_valid(self, form):
        logger.info("Processing assistant update submission.")
        logger.info("Form data: " + str(self.request.POST))

        with transaction.atomic():
            # Fetch the original (pre-update) state of the object from the database
            original_object = Assistant.objects.get(id=self.object.id)

            # Update the assistant locally but don't commit yet
            self.object = form.save(commit=False)

            # Determine if relevant fields have changed
            relevant_fields_changed = False
            for field in ["name", "model", "instructions", "metadata"]:
                if form.cleaned_data.get(field) != getattr(original_object, field):
                    logger.debug(
                        f"Field {field} has changed: {getattr(original_object, field)} -> {form.cleaned_data.get(field)}"
                    )
                    relevant_fields_changed = True
                    break
            else:
                # Special handling for many-to-many 'files' field
                form_file_ids = set(
                    form.cleaned_data.get("files").values_list("id", flat=True)
                )
                original_file_ids = set(
                    original_object.files.values_list("id", flat=True)
                )
                if form_file_ids != original_file_ids:
                    logger.debug(
                        f"Field files has changed: {original_file_ids} -> {form_file_ids}"
                    )
                    relevant_fields_changed = True

            if relevant_fields_changed:
                user_provided_name = form.cleaned_data.get("name", "")

                # Generate new assistant prefixed_name with prefix
                prefix = f"1g_{self.request.user.id}_"
                self.object.prefixed_name = prefix + user_provided_name

                form_files = form.cleaned_data.get("files", [])

                # Prepare the payload for updating the assistant in OpenAI
                update_payload = {
                    "model": self.object.model,
                    "instructions": self.object.instructions,
                    "metadata": self.object.metadata,
                    "name": self.object.prefixed_name,
                    "file_ids": [doc.id for doc in form_files],
                }

                try:
                    # Retrieve OpenAI API key and update the assistant in OpenAI
                    api_key_id = self.request.POST.get("apikey")
                    api_key = APIKey.objects.get(id=api_key_id).key

                    response = AssistantUploader.update_assistant_in_openai(
                        openai_key=api_key,
                        openai_id=self.object.openai_id,
                        update_payload=update_payload,
                    )
                except Exception as exc:
                    # Log the error and raise to trigger a rollback
                    logger.error(
                        f"An error occurred while updating assistant in OpenAI: {str(exc)}"
                    )
                    form.add_error(
                        None, f"An error occurred during OpenAI update: {str(exc)}"
                    )
                    return self.form_invalid(form)
                else:
                    logger.info("Assistant updated in OpenAI: " + str(response))

            # Commit the changes to the local database as OpenAI update is successful
            self.object.save()

        logger.info("Assistant update processed successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("dashboard:assistant_detail", kwargs={"pk": self.object.pk})
