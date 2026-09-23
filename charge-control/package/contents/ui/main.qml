import QtQuick
import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasmoid
import org.kde.plasma.plasma5support as Plasma5Support

PlasmoidItem {
    id: root

    // The package is installed in ~/.local/share, which survives SteamOS updates.
    readonly property string helper: "/home/deck/.local/share/plasma/plasmoids/" +
        "local.onexfly.charge-toggle/contents/scripts/charge-control"
    property string mode: ""
    property string charge: "?"
    property string limit: "?"
    property string batteryStatus: ""
    property string statusError: ""
    property string actionError: ""
    property bool busy: false

    readonly property bool blocked: mode === "inhibit-charge" || mode === "inhibit-charge-awake"
    readonly property bool chargingDespiteBlock: blocked && batteryStatus === "Charging"
    readonly property bool chargingDespiteLimit: mode === "auto" &&
        Number(charge) > Number(limit) && batteryStatus === "Charging"
    readonly property string errorText: actionError || statusError
    // A lock is easy to distinguish from Plasma's own battery indicator.
    readonly property string iconName: errorText || !mode || chargingDespiteBlock ? "dialog-warning" :
        blocked ? "object-locked" : "object-unlocked"

    Plasmoid.icon: iconName
    Plasmoid.status: errorText || !mode || chargingDespiteBlock ?
        PlasmaCore.Types.NeedsAttentionStatus : PlasmaCore.Types.ActiveStatus
    toolTipMainText: chargingDespiteBlock ? "Запрет задан, но батарея сообщает о зарядке" :
        chargingDespiteLimit ? "Зарядка идёт выше заданного лимита" :
        blocked ? "Запрет зарядки задан" : mode === "auto" ?
        "Автоматический режим зарядки" : "Состояние зарядки неизвестно"
    toolTipSubText: errorText || ("Аккумулятор: " + charge + "% · лимит: " +
        limit + "% · статус: " + batteryStatus + " · режим: " + mode +
        "\nНажмите, чтобы переключить")
    activationTogglesExpanded: false
    preferredRepresentation: compactRepresentation

    function refresh() {
        if (!busy) {
            commands.connectSource(helper + " status")
        }
    }

    function toggle() {
        if (busy) {
            return
        }
        busy = true
        actionError = ""
        commands.connectSource(helper + (blocked ? " allow" : " block"))
    }

    Plasma5Support.DataSource {
        id: commands
        engine: "executable"
        connectedSources: []

        onNewData: (sourceName, data) => {
            disconnectSource(sourceName)
            const exitCode = Number(data["exit code"])
            const output = String(data["stdout"] || "").trim()
            const error = String(data["stderr"] || "").trim()
            if (sourceName.endsWith(" status")) {
                if (exitCode !== 0) {
                    root.mode = ""
                    root.charge = "?"
                    root.limit = "?"
                    root.batteryStatus = ""
                    root.statusError = error || "Не удалось прочитать состояние зарядки"
                    return
                }
                const parts = output.split("|")
                if (parts.length !== 4) {
                    root.mode = ""
                    root.statusError = "Неожиданный ответ контроллера"
                    return
                }
                root.mode = parts[0]
                root.charge = parts[1]
                root.limit = parts[2]
                root.batteryStatus = parts[3]
                root.statusError = ""
            } else {
                root.busy = false
                if (exitCode !== 0) {
                    root.actionError = error || "Не удалось переключить зарядку"
                }
                root.refresh()
            }
        }
    }

    Timer {
        interval: 5000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: root.refresh()
    }

    compactRepresentation: MouseArea {
        implicitWidth: Kirigami.Units.iconSizes.medium
        implicitHeight: Kirigami.Units.iconSizes.medium
        hoverEnabled: true
        enabled: !root.busy
        onClicked: root.toggle()

        Kirigami.Icon {
            anchors.fill: parent
            source: root.iconName
            opacity: root.busy ? 0.5 : 1
        }
    }

    fullRepresentation: PlasmaComponents.Label {
        text: root.toolTipMainText + "\n" + root.toolTipSubText
        padding: Kirigami.Units.largeSpacing
    }
}
