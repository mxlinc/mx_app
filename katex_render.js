/**
 * KaTeX server-side renderer.
 * Called by Python via subprocess. Reads a JSON payload from stdin:
 *   { "latex": "...", "displayMode": true|false }
 * Writes rendered HTML to stdout, exits 0 on success or 1 on error.
 */
const katex = require('katex');
const chunks = [];
process.stdin.on('data', d => chunks.push(d));
process.stdin.on('end', () => {
    try {
        const { latex, displayMode } = JSON.parse(chunks.join(''));
        const html = katex.renderToString(latex, {
            displayMode: !!displayMode,
            throwOnError: false,
            output: 'html'
        });
        process.stdout.write(html);
        process.exit(0);
    } catch (e) {
        process.stderr.write(e.message || String(e));
        process.exit(1);
    }
});
