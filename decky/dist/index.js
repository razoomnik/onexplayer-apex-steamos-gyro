const manifest = { name: "Apex Fixes", author: "Apex Fixes Project", flags: ["_root"], api_version: 1 };
const API_VERSION = 2;
const internalAPIConnection = window.__DECKY_SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED_deckyLoaderAPIInit;
if (!internalAPIConnection) {
  throw new Error("[@decky/api]: Failed to connect to Decky Loader API.");
}
let api;
try {
  api = internalAPIConnection.connect(API_VERSION, manifest.name);
} catch (_error) {
  api = internalAPIConnection.connect(1, manifest.name);
  console.warn("Apex Fixes: Decky Loader API v2 unavailable; using v1 compatibility mode.");
}
const callable = api.callable;
const toaster = api.toaster;
const definePlugin = (fn) => (...args) => fn(...args);

const { ButtonItem, PanelSection, PanelSectionRow, staticClasses } = DFL;
const ToggleField = DFL.ToggleField;
const { useEffect, useState, useRef } = SP_REACT;
const { jsx, jsxs, Fragment } = SP_JSX;

const getFixes = callable("get_fixes");
const runFix = callable("run_fix");
const getLedState = callable("get_led_state");
const setLedEnabled = callable("set_led_enabled");
const getChargeState = callable("get_charge_state");
const setChargeBlocked = callable("set_charge_blocked");

function ToolIcon() {
  return jsx("svg", {
    width: "1em",
    height: "1em",
    viewBox: "0 0 24 24",
    fill: "currentColor",
    "aria-hidden": "true",
    children: jsx("path", {
      d: "M22.7 19.3 14.6 11.2a6.5 6.5 0 0 0-8.2-8.1l3.7 3.7-3.3 3.3-3.7-3.7a6.5 6.5 0 0 0 8.1 8.2l8.1 8.1a1 1 0 0 0 1.4 0l2-2a1 1 0 0 0 0-1.4Z"
    })
  });
}

function ChargeControl() {
  const [state, setState] = useState(null);
  const [busy, setBusy] = useState(false);
  const mounted = useRef(false);
  const changing = useRef(false);
  const generation = useRef(0);

  useEffect(() => {
    mounted.current = true;
    let active = true;
    const refresh = async () => {
      if (changing.current) return;
      const current = generation.current;
      try {
        const next = await getChargeState();
        if (active && current === generation.current) setState(next);
      } catch (error) {
        if (active && current === generation.current) {
          setState({ available: false, message: String(error) });
        }
      }
    };
    refresh();
    const timer = setInterval(refresh, 5000);
    return () => { active = false; mounted.current = false; clearInterval(timer); };
  }, []);

  const change = async (blocked) => {
    if (changing.current || !state?.available) return;
    changing.current = true;
    generation.current += 1;
    setBusy(true);
    try {
      const result = await setChargeBlocked(blocked);
      if (mounted.current) setState(result);
      if (!result.ok) toaster.toast({ title: "Charge control failed", body: result.message });
    } catch (error) {
      if (mounted.current) setState({ available: false, message: String(error) });
      toaster.toast({ title: "Charge control failed", body: String(error) });
    } finally {
      changing.current = false;
      if (mounted.current) setBusy(false);
    }
  };

  const description = busy ? "Applying…" : !state ? "Reading battery…" :
    !state.available ? (state.message || "Battery control unavailable") :
    `Battery ${state.capacity}% · ${state.battery_status}. ` +
    (state.blocked && state.battery_status === "Charging"
      ? "Block is set, but the battery reports charging. Status can take several seconds to update."
      : state.blocked ? "Charging is blocked." : "Charging is allowed.");
  return jsx(PanelSection, {
    title: "Battery",
    children: jsx(PanelSectionRow, {
      children: ToggleField ? jsx(ToggleField, {
        label: "Block charging", description,
        checked: state?.blocked === true,
        disabled: busy || !state?.available,
        onChange: change
      }) : jsxs(Fragment, { children: [
        jsx("div", { children: description }),
        jsx(ButtonItem, {
          layout: "below", disabled: busy || !state?.available,
          onClick: () => change(!state?.blocked),
          children: state?.blocked ? "Allow charging" : "Block charging"
        })
      ] })
    })
  });
}

function Content() {
  const [fixes, setFixes] = useState([]);
  const [running, setRunning] = useState(null);
  const [status, setStatus] = useState("Loading…");
  const [ledAvailable, setLedAvailable] = useState(false);
  const [ledEnabled, setLedEnabledState] = useState(null);
  const [ledBusy, setLedBusy] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.all([getFixes(), getLedState()])
      .then(([items, led]) => {
        if (!active) return;
        setFixes(items);
        setLedAvailable(led.available);
        setLedEnabledState(led.enabled);
        setStatus("Ready");
      })
      .catch((error) => {
        if (!active) return;
        console.error("Apex Fixes: failed to initialize", error);
        setStatus("Backend unavailable");
      });
    return () => {
      active = false;
    };
  }, []);

  const applyFix = async (fix) => {
    if (running !== null || ledBusy) return;
    setRunning(fix.id);
    setStatus(`Running ${fix.title}…`);
    try {
      const result = await runFix(fix.id);
      setStatus(result.message);
      toaster.toast({
        title: result.ok ? `${fix.title} complete` : `${fix.title} failed`,
        body: result.message
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setStatus(`Failed: ${message}`);
      toaster.toast({ title: `${fix.title} failed`, body: message });
    } finally {
      setRunning(null);
    }
  };

  const changeLedState = async (next) => {
    if (ledBusy || running !== null || !ledAvailable) return;
    setLedBusy(true);
    setStatus(`Turning joystick LEDs ${next ? "on" : "off"}…`);
    try {
      const result = await setLedEnabled(next);
      if (result.ok && typeof result.enabled === "boolean") {
        setLedEnabledState(result.enabled);
      }
      setStatus(result.message);
      toaster.toast({
        title: result.ok ? "Joystick LEDs updated" : "Joystick LED control failed",
        body: result.message
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      setStatus(`Failed: ${message}`);
      toaster.toast({ title: "Joystick LED control failed", body: message });
    } finally {
      setLedBusy(false);
    }
  };

  const ledDescription = !ledAvailable
    ? "Apex RGB HID was not found."
    : ledEnabled === null
      ? "Direct Apex RGB control. Current state is unknown until the first change."
      : `Direct Apex RGB control. Saved state: ${ledEnabled ? "On" : "Off"}.`;

  let ledControl;
  if (ToggleField) {
    ledControl = jsx(ToggleField, {
      label: "Joystick LEDs",
      description: ledDescription,
      checked: ledEnabled ?? true,
      disabled: !ledAvailable || ledBusy || running !== null,
      onChange: (value) => changeLedState(value)
    });
  } else {
    ledControl = jsxs(Fragment, {
      children: [
        jsx("div", {
          style: { fontSize: "14px", fontWeight: 600, marginBottom: "4px" },
          children: "Joystick LEDs"
        }),
        jsx("div", {
          style: { fontSize: "12px", opacity: 0.72, marginBottom: "8px", lineHeight: 1.35 },
          children: ledDescription
        }),
        jsx(ButtonItem, {
          layout: "below",
          disabled: !ledAvailable || ledBusy || running !== null,
          onClick: () => changeLedState(!(ledEnabled ?? true)),
          children: ledBusy
            ? "Applying…"
            : ledEnabled === false
              ? "Turn LEDs On"
              : "Turn LEDs Off"
        })
      ]
    });
  }

  return jsxs(Fragment, {
    children: [
      jsx(ChargeControl, {}),
      jsx(PanelSection, {
        title: "Controller",
        children: jsx(PanelSectionRow, { children: ledControl })
      }),
      jsx(PanelSection, {
        title: "Recovery fixes",
        children: fixes.map((fix) =>
          jsx("div", {
            children: jsx(PanelSectionRow, {
              children: jsxs(Fragment, {
                children: [
                  jsx("div", {
                    style: { fontSize: "14px", fontWeight: 600, marginBottom: "4px" },
                    children: fix.title
                  }),
                  jsx("div", {
                    style: { fontSize: "12px", opacity: 0.72, marginBottom: "8px", lineHeight: 1.35 },
                    children: fix.description
                  }),
                  jsx(ButtonItem, {
                    layout: "below",
                    disabled: running !== null || ledBusy,
                    onClick: () => applyFix(fix),
                    children: running === fix.id ? "Applying…" : fix.button_label
                  })
                ]
              })
            })
          }, fix.id)
        )
      }),
      jsx(PanelSection, {
        title: "Status",
        children: jsx(PanelSectionRow, {
          children: jsx("div", {
            style: { fontSize: "12px", opacity: 0.8 },
            children: status
          })
        })
      })
    ]
  });
}

const plugin = definePlugin(() => ({
  name: "Apex Fixes",
  titleView: jsx("div", { className: staticClasses.Title, children: "Apex Fixes" }),
  content: jsx(Content, {}),
  icon: jsx(ToolIcon, {}),
  onDismount() {
    console.log("Apex Fixes unloaded");
  }
}));

export { plugin as default };
