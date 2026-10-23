const assert = require('node:assert/strict');
const path = require('node:path');
const {test} = require('node:test');

const OHSHotspot = require(path.join(__dirname, '..', 'static', 'js', 'ohs-hotspot.js'));

// The original player hit test, kept verbatim. Legacy hotspots (no `units`) must keep
// matching it exactly, so saved questions are never re-interpreted by later changes.
function originalLegacyHit(hs, nx, ny) {
    return !!(hs && nx >= hs.x && nx <= hs.x + hs.width
                 && ny >= hs.y && ny <= hs.y + hs.height);
}

test('legacy hotspot (no units) is read as natural-image pixels, unchanged', () => {
    const legacy = {id: 'hs1', x: 511, y: 50, width: 34, height: 54};

    assert.deepEqual(OHSHotspot.toNaturalPixels(legacy, 1200, 300), {x: 511, y: 50, width: 34, height: 54});
    // Image size must not influence legacy interpretation.
    assert.deepEqual(OHSHotspot.toNaturalPixels(legacy, 0, 0), {x: 511, y: 50, width: 34, height: 54});
});

test('legacy hit test matches the original player logic at every sampled point', () => {
    const legacy = {id: 'hs1', x: 511, y: 50, width: 34, height: 54};
    for (let x = 500; x <= 560; x += 0.5) {
        for (let y = 40; y <= 110; y += 0.5) {
            assert.equal(OHSHotspot.containsPoint(legacy, x, y, 1200, 300), originalLegacyHit(legacy, x, y), `at ${x},${y}`);
        }
    }
});

test('new hotspots are stored as fractions of the natural image size', () => {
    const stored = OHSHotspot.fromNaturalPixels({x: 300, y: 50, width: 120, height: 60}, 1200, 400, 'hs1');

    assert.deepEqual(stored, {id: 'hs1', units: 'fraction', x: 0.25, y: 0.125, width: 0.1, height: 0.15});
});

test('fraction hotspots map to the same pixels at any natural size', () => {
    const stored = {id: 'hs1', units: 'fraction', x: 0.25, y: 0.125, width: 0.1, height: 0.15};

    assert.deepEqual(OHSHotspot.toNaturalPixels(stored, 1200, 400), {x: 300, y: 50, width: 120, height: 60});
    assert.deepEqual(OHSHotspot.toNaturalPixels(stored, 2400, 800), {x: 600, y: 100, width: 240, height: 120});
    assert.equal(OHSHotspot.containsPoint(stored, 360, 80, 1200, 400), true);
    assert.equal(OHSHotspot.containsPoint(stored, 200, 80, 1200, 400), false);
});

test('round trip through the stored format preserves the drawn rectangle', () => {
    const drawn = {x: 123.4, y: 56.7, width: 89.1, height: 23.4};
    const back = OHSHotspot.toNaturalPixels(OHSHotspot.fromNaturalPixels(drawn, 1537, 611), 1537, 611);

    for (const key of ['x', 'y', 'width', 'height']) {
        assert.ok(Math.abs(back[key] - drawn[key]) < 0.01, key);
    }
});

test('fractions are clamped inside the image', () => {
    const stored = OHSHotspot.fromNaturalPixels({x: 1150, y: -5, width: 200, height: 50}, 1200, 400);

    assert.ok(stored.x + stored.width <= 1);
    assert.equal(stored.y, 0);
});

test('unknown units are never guessed', () => {
    const future = {id: 'hs1', units: 'something-else', x: 0.1, y: 0.1, width: 0.5, height: 0.5};

    assert.equal(OHSHotspot.toNaturalPixels(future, 1000, 1000), null);
    assert.equal(OHSHotspot.containsPoint(future, 300, 300, 1000, 1000), false);
});

test('fraction hotspots need the image size', () => {
    const stored = {id: 'hs1', units: 'fraction', x: 0.1, y: 0.1, width: 0.5, height: 0.5};

    assert.equal(OHSHotspot.toNaturalPixels(stored, 0, 0), null);
    assert.equal(OHSHotspot.toNaturalPixels(null, 100, 100), null);
});
