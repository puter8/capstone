import { doesNotMatch, equal, match } from "node:assert/strict";
import React, { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { NameEditDialog } from "../components/dialogs/NameEditDialog";
import { DISPLAY_NAME_MAX_LENGTH } from "../lib/display-name";

// tsx compiles JSX the classic way here, while Next uses the automatic runtime.
(globalThis as { React?: typeof React }).React = React;

equal(DISPLAY_NAME_MAX_LENGTH, 30, "The backend accepts 1-30 characters");

const render = (error?: string | null) => renderToStaticMarkup(
  createElement(NameEditDialog, { error, initialName: "Claire", onCancel: () => {}, onConfirm: () => {} }),
);

const markup = render();
match(markup, /<input[^>]*value="Claire"/, "The dialog starts with the current name");
match(markup, new RegExp(`<input[^>]*maxLength="${DISPLAY_NAME_MAX_LENGTH}"`), "The name input must stop at the backend limit");
doesNotMatch(markup, /role="alert"/, "No error line before anything failed");

// The page behind the dialog is covered by it, so a failed save has to be shown inside the dialog.
const failed = render("이름을 변경하지 못했어요.");
match(failed, /<p[^>]*role="alert"[^>]*>이름을 변경하지 못했어요\.<\/p>/, "A failed save is shown inside the dialog");
doesNotMatch(render(null), /role="alert"/);

console.log("Name edit dialog checks passed: 30-character limit and a failed save shown inside the dialog.");
