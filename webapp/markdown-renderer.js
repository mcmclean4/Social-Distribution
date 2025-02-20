import { marked } from "marked"; // Import the markdown converter

document.addEventListener("DOMContentLoaded", function () {
    const contentDiv = document.querySelector('.content'); // Target only content block

    if (contentDiv) {
        const contentType = contentDiv.getAttribute('data-content-type');

        if (contentType === "text/markdown") { // Only apply markdown if contentType is markdown
            console.log("Applying Markdown Parsing:", contentDiv.textContent.trim());
            contentDiv.innerHTML = marked.parse(contentDiv.textContent.trim());
        } else {
            console.log("Markdown not applied. Content type is:", contentType);
        }
    }
});