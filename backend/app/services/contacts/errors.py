from __future__ import annotations


class ContactError(Exception):
    """Erreur métier contact."""

    status_code = 400
    code = "contact_error"

    def __init__(self, message: str = "Erreur contact"):
        self.message = message
        super().__init__(message)


class ContactNotFoundError(ContactError):
    status_code = 404
    code = "contact_not_found"

    def __init__(self, message: str = "Contact introuvable"):
        super().__init__(message)


class DuplicateContactError(ContactError):
    status_code = 409
    code = "duplicate_contact"

    def __init__(self, message: str = "Un contact similaire existe déjà"):
        super().__init__(message)


class ContactWorkspaceMismatchError(ContactError):
    status_code = 403
    code = "contact_workspace_mismatch"

    def __init__(self, message: str = "Contact hors de votre espace"):
        super().__init__(message)


class DocumentWorkspaceMismatchError(ContactError):
    status_code = 403
    code = "document_workspace_mismatch"

    def __init__(self, message: str = "Document hors de votre espace"):
        super().__init__(message)


class InvalidContactDataError(ContactError):
    status_code = 422
    code = "invalid_contact_data"


class UnsafeBankDetailUpdateError(ContactError):
    status_code = 409
    code = "unsafe_bank_detail_update"

    def __init__(self, message: str = "Mise à jour IBAN refusée sans confirmation explicite"):
        super().__init__(message)


class ContactSuggestionAlreadyResolvedError(ContactError):
    status_code = 409
    code = "suggestion_already_resolved"

    def __init__(self, message: str = "Cette suggestion a déjà été traitée"):
        super().__init__(message)
