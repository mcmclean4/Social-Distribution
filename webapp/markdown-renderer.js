import { marked } from "marked";

document.addEventListener("DOMContentLoaded", function () {
    const contentDiv = document.querySelector('.content');
    const debugMarkdownDiv = document.getElementById('debug-markdown');

    // FIRST LINE DOESN'T RENDER AS MARKDOWN
    // Not sure why, think bootstrap is interfering but can't figure it out
    // was last working at this commit:
    // https://github.com/uofa-cmput404/w25-project-mod-cornsilk/commit/b7e84aa5e1d2e61646d2e2411534b7324823bd13


    if (contentDiv && debugMarkdownDiv) {
        let rawMarkdown = debugMarkdownDiv.textContent.trim(); // Get the raw Markdown
        console.log("🔹 Raw Markdown Before Processing:", JSON.stringify(rawMarkdown));

        // Normalize line breaks: Convert single newlines to double newlines
        let formattedMarkdown = rawMarkdown.replace(/^(.+)\n/g, "$1\n\n");
        console.log("🔹 Formatted Markdown (Before Parsing):", JSON.stringify(formattedMarkdown));

        // Convert Markdown to HTML
        let parsedHTML = marked.parse(formattedMarkdown);
        console.log("🔹 Parsed HTML Output:", parsedHTML);

        // Apply the converted Markdown
        contentDiv.innerHTML = parsedHTML;

        console.log("✅ Markdown applied successfully!");
    } else {
        console.log("❌ Content div or debug div not found.");
    }
});
