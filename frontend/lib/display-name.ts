// Matches the backend rule in _validate_display_name (1-30 characters after trimming).
// The input counts UTF-16 units, so an emoji uses two; the client can only be stricter.
export const DISPLAY_NAME_MAX_LENGTH = 30;
