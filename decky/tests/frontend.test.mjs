import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import test from 'node:test';

function harness(rpc) {
  const hooks = [];
  let cursor = 0;
  let timer;
  const ui = { ToggleField: 'Toggle', PanelSection: 'Panel', PanelSectionRow: 'Row', staticClasses: {} };
  const context = vm.createContext({
    console, DFL: ui,
    window: { __DECKY_SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED_deckyLoaderAPIInit: {
      connect: () => ({ callable: name => (...args) => rpc[name](...args), toaster: { toast() {} } })
    } },
    SP_JSX: { jsx: (type, props) => ({ type, props }), jsxs: (type, props) => ({ type, props }), Fragment: 'Fragment' },
    SP_REACT: {
      useState: initial => { const i = cursor++; if (!(i in hooks)) hooks[i] = initial; return [hooks[i], next => { hooks[i] = next; }]; },
      useRef: initial => { const i = cursor++; return hooks[i] ??= { current: initial }; },
      useEffect: effect => { const i = cursor++; if (!(i in hooks)) hooks[i] = effect(); }
    },
    setInterval: fn => { timer = fn; return 1; }, clearInterval() {}
  });
  const source = readFileSync(new URL('../src/index.js', import.meta.url), 'utf8').replace('export { plugin as default };', 'globalThis.renderCharge = ChargeControl;');
  vm.runInContext(source, context);
  return { render: () => { cursor = 0; return context.renderCharge().props.children.props.children.props; }, poll: () => timer() };
}
const flush = () => new Promise(resolve => setImmediate(resolve));

test('reflects hardware state and confirms toggles through backend', async () => {
  const calls = [];
  const h = harness({
    get_charge_state: async () => ({ available: true, blocked: true, capacity: 92, battery_status: 'Not charging' }),
    set_charge_blocked: async blocked => { calls.push(blocked); return { ok: true, available: true, blocked, capacity: 92, battery_status: 'Charging' }; }
  });
  assert.equal(h.render().disabled, true);
  await flush();
  assert.equal(h.render().checked, true);
  await h.render().onChange(false);
  assert.deepEqual(calls, [false]);
  assert.equal(h.render().checked, false);
});

test('missing battery disables the control with an explanation', async () => {
  const h = harness({ get_charge_state: async () => ({ available: false, message: 'Battery missing' }) });
  h.render(); await flush();
  assert.equal(h.render().disabled, true);
  assert.equal(h.render().description, 'Battery missing');
});

test('a stale in-flight poll cannot undo a confirmed toggle', async () => {
  let resolvePoll;
  let first = true;
  const h = harness({
    get_charge_state: () => first ? (first = false, Promise.resolve({ available: true, blocked: false })) : new Promise(resolve => { resolvePoll = resolve; }),
    set_charge_blocked: async () => ({ ok: true, available: true, blocked: true, capacity: 92, battery_status: 'Not charging' })
  });
  h.render(); await flush();
  const poll = h.poll();
  await h.render().onChange(true);
  resolvePoll({ available: true, blocked: false }); await poll;
  assert.equal(h.render().checked, true);
});
