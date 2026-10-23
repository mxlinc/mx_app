/**
 * ohs-hotspot.js
 *
 * Single source of truth for how an OHS hotspot (question.image.hotspot) is stored
 * and interpreted. Both the builder (quiz-builder-form.js) and the player
 * (template-handlers.js) must go through these functions.
 *
 * Stored formats:
 *   Legacy (no `units` key): x / y / width / height are pixels of the image's
 *     natural (full) size. Written by builders before units were introduced.
 *   units: "fraction": x / y / width / height are fractions (0–1) of the image's
 *     natural width / height. Independent of how large the image is displayed.
 *
 * Compatibility rules:
 *   - Never change how an existing format is interpreted. Saved questions depend on it.
 *   - To change the format again, add a new `units` value plus a new branch in
 *     toNaturalPixels(), and make the builder write the new value.
 *   - Unknown `units` values resolve to null (no hotspot) rather than being guessed.
 */
(function (root) {
    'use strict';

    const UNITS_FRACTION = 'fraction';
    const FRACTION_DECIMALS = 6;

    function clamp(value, min, max) {
        return Math.max(min, Math.min(max, value));
    }

    function roundTo(value, decimals) {
        const factor = Math.pow(10, decimals);
        return Math.round(value * factor) / factor;
    }

    /** Stored hotspot -> {x, y, width, height} in natural image pixels, or null. */
    function toNaturalPixels(hotspot, naturalWidth, naturalHeight) {
        if (!hotspot) return null;

        if (hotspot.units === undefined || hotspot.units === null) {
            return {
                x: hotspot.x,
                y: hotspot.y,
                width: hotspot.width,
                height: hotspot.height
            };
        }

        if (hotspot.units === UNITS_FRACTION) {
            if (!naturalWidth || !naturalHeight) return null;
            return {
                x: hotspot.x * naturalWidth,
                y: hotspot.y * naturalHeight,
                width: hotspot.width * naturalWidth,
                height: hotspot.height * naturalHeight
            };
        }

        return null;
    }

    /** Rectangle in natural image pixels -> hotspot in the current storage format. */
    function fromNaturalPixels(rect, naturalWidth, naturalHeight, id) {
        if (!rect || !naturalWidth || !naturalHeight) return null;

        const x = clamp(rect.x / naturalWidth, 0, 1);
        const y = clamp(rect.y / naturalHeight, 0, 1);
        const width = clamp(rect.width / naturalWidth, 0, 1 - x);
        const height = clamp(rect.height / naturalHeight, 0, 1 - y);

        return {
            id: id || 'hs1',
            units: UNITS_FRACTION,
            x: roundTo(x, FRACTION_DECIMALS),
            y: roundTo(y, FRACTION_DECIMALS),
            width: roundTo(width, FRACTION_DECIMALS),
            height: roundTo(height, FRACTION_DECIMALS)
        };
    }

    /** True if the point (natural image pixels) lies inside the hotspot (edges inclusive). */
    function containsPoint(hotspot, px, py, naturalWidth, naturalHeight) {
        const r = toNaturalPixels(hotspot, naturalWidth, naturalHeight);
        if (!r) return false;
        return px >= r.x && px <= r.x + r.width
            && py >= r.y && py <= r.y + r.height;
    }

    const api = {
        UNITS_FRACTION: UNITS_FRACTION,
        toNaturalPixels: toNaturalPixels,
        fromNaturalPixels: fromNaturalPixels,
        containsPoint: containsPoint
    };

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
    }
    root.OHSHotspot = api;
})(typeof window !== 'undefined' ? window : globalThis);
