const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');

const template = fs.readFileSync(path.join(__dirname, '..', 'templates', 'units_list.html'), 'utf8');
const script = template.match(/{% block scripts %}\s*<script>([\s\S]*?)<\/script>/)[1];

function fixture(items) {
    const button = {hidden: true, disabled: true};
    const list = {
        children: [],
        querySelectorAll() { return this.children.filter(row => row.dataset); },
    };
    function node(properties = {}) {
        return {
            ...properties,
            replaceWith(replacement) {
                const index = list.children.indexOf(this);
                assert.notEqual(index, -1);
                list.children.splice(index, 1, replacement);
            },
            remove() {
                list.children.splice(list.children.indexOf(this), 1);
            },
        };
    }
    list.children = items.map(item => node({
        dataset: {
            code: item.code,
            quizSortId: String(Number(item.code.slice(2))),
        },
        checkbox: item.code.startsWith('Q-')
            ? {checked: Boolean(item.checked), disabled: Boolean(item.disabled)}
            : null,
        querySelector() {
            return this.checkbox && this.checkbox.checked && !this.checkbox.disabled
                ? this.checkbox : null;
        },
    }));
    const context = vm.createContext({
        document: {
            getElementById(id) {
                if (id === 'cu-item-list') return list;
                if (id === 'cu-sort-btn') return button;
                return {style: {}, addEventListener() {}};
            },
            createComment() { return node(); },
            querySelectorAll() { return list.querySelectorAll(); },
        },
        fetch() { throw new Error('Sorting must not send a request'); },
    });
    vm.runInContext(script, context);
    return {context, list, button};
}

test('sorts only selected quiz slots numerically, keeping the same unselected nodes', () => {
    const {context, list} = fixture([
        {code: 'V-0001'}, {code: 'Q-30', checked: true}, {code: 'Q-20'},
        {code: 'I-0001'}, {code: 'Q-10', checked: true}, {code: 'unknown'},
        {code: 'Q-2', checked: true}, {code: 'V-0002'},
    ]);
    const original = [...list.children];
    context.sortSelectedQuizzes();
    assert.deepEqual(list.children.map(row => row.dataset.code), [
        'V-0001', 'Q-2', 'Q-20', 'I-0001', 'Q-10', 'unknown', 'Q-30', 'V-0002',
    ]);
    for (const index of [0, 2, 3, 5, 7]) assert.equal(list.children[index], original[index]);
    assert.equal(list.children[1], original[6]);
    assert.equal(list.children[4], original[4]);
    assert.equal(list.children[6], original[1]);
    assert.ok(context.selectedQuizRows().every(row => row.checkbox.checked));
});

test('button is hidden with no selection, disabled with one, and enabled with two', () => {
    const {context, list, button} = fixture([{code: 'Q-10'}, {code: 'Q-2'}]);
    context.updateQuizSortButton();
    assert.equal(button.hidden, true);
    assert.equal(button.disabled, true);
    list.children[0].checkbox.checked = true;
    context.updateQuizSortButton();
    assert.equal(button.hidden, false);
    assert.equal(button.disabled, true);
    list.children[1].checkbox.checked = true;
    context.updateQuizSortButton();
    assert.equal(button.hidden, false);
    assert.equal(button.disabled, false);
    list.children.forEach(row => { row.checkbox.checked = false; });
    context.updateQuizSortButton();
    assert.equal(button.hidden, true);
});

test('zero or one selected quiz leaves the list unchanged', () => {
    for (const checked of [false, true]) {
        const {context, list} = fixture([{code: 'Q-10', checked}, {code: 'Q-2'}, {code: 'V-1'}]);
        const original = [...list.children];
        context.sortSelectedQuizzes();
        assert.deepEqual(list.children, original);
    }
});

test('equal numeric suffixes retain their relative order', () => {
    const {context, list} = fixture([
        {code: 'Q-010', checked: true}, {code: 'Q-10', checked: true},
        {code: 'V-1'}, {code: 'Q-2', checked: true}, {code: 'Q-010', checked: true},
    ]);
    const original = [...list.children];
    context.sortSelectedQuizzes();
    assert.deepEqual(list.children, [original[3], original[0], original[2], original[1], original[4]]);
});

test('sorting respects current positions after manual reordering', () => {
    const {context, list} = fixture([
        {code: 'Q-30', checked: true}, {code: 'Q-2', checked: true},
        {code: 'V-1'}, {code: 'Q-10'},
    ]);
    const original = [...list.children];
    list.children = [original[0], original[2], original[3], original[1]];
    context.sortSelectedQuizzes();
    assert.deepEqual(list.children, [original[1], original[2], original[3], original[0]]);
});

test('removing a selected quiz updates the button', () => {
    const {context, list, button} = fixture([
        {code: 'Q-10', checked: true}, {code: 'Q-2', checked: true},
    ]);
    context.updateQuizSortButton();
    const first = list.children[0];
    context.removeItem({closest() { return first; }});
    assert.equal(button.hidden, false);
    assert.equal(button.disabled, true);
    const last = list.children[0];
    context.removeItem({closest() { return last; }});
    assert.equal(button.hidden, true);
});

test('disabled selections are ignored', () => {
    const {context, list, button} = fixture([
        {code: 'Q-bad', checked: true, disabled: true},
        {code: 'Q-10', checked: true}, {code: 'Q-2', checked: true},
    ]);
    const invalid = list.children[0];
    context.sortSelectedQuizzes();
    assert.equal(list.children[0], invalid);
    assert.deepEqual(list.children.map(row => row.dataset.code), ['Q-bad', 'Q-2', 'Q-10']);
    assert.equal(button.disabled, false);
});

test('validates quiz codes and handles padding numerically', () => {
    const {context} = fixture([]);
    for (const [code, expected] of [['Q-0002', 2], ['Q-10', 10], ['Q-0', 0]]) {
        assert.equal(context.quizSortId(code), expected);
    }
    for (const code of ['Q-bad', 'Q-', 'Q-1x', 'Q--1', 'Q-1.5', 'V-2', 'Q-9007199254740992']) {
        assert.equal(context.quizSortId(code), null);
    }
});

test('sorting twice is idempotent and never calls the server', () => {
    const {context, list} = fixture([
        {code: 'Q-10', checked: true}, {code: 'I-1'}, {code: 'Q-2', checked: true},
    ]);
    context.sortSelectedQuizzes();
    const sorted = [...list.children];
    context.sortSelectedQuizzes();
    assert.deepEqual(list.children, sorted);
});
