import { marked } from "marked"; // Import the markdown converter

// Handle rendering
document.addEventListener("DOMContentLoaded", function () {
    const contentDiv = document.querySelector('.content'); // Target only content block
    if (contentDiv) {
        console.log("Before Markdown Parsing:", contentDiv.innerHTML);
        contentDiv.innerHTML = marked.parse(contentDiv.textContent.trim());
        console.log("After Markdown Parsing:", contentDiv.innerHTML);
    }
});