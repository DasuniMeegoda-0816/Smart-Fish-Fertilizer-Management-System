
const assignmentTable =
    document.getElementById("assignmentTable");

const completedTable =
    document.getElementById("completedTable");

const collectorMessage =
    document.getElementById("collectorMessage");

function addCell(row, value) {
    const cell = document.createElement("td");
    cell.textContent = value;
    row.appendChild(cell);
    return cell;
}

function showEmpty(table, columns, message) {
    const row = document.createElement("tr");
    const cell = addCell(row, message);
    cell.colSpan = columns;
    table.appendChild(row);
}

async function loadAssignments() {
    try {
        const response = await fetch("/api/collector/assignments");

        if (!response.ok) {
            throw new Error("Cannot load assignments");
        }

        const records = await response.json();

        assignmentTable.replaceChildren();
        completedTable.replaceChildren();

        document.getElementById("totalCount").textContent =
            records.length;

        const assigned = records.filter(
            record => record.status === "Assigned"
        );

        const collected = records.filter(
            record => record.status === "Collected"
        );

        document.getElementById("assignedCount").textContent =
            assigned.length;

        document.getElementById("collectedCount").textContent =
            collected.length;

        if (assigned.length === 0) {
            showEmpty(
                assignmentTable, 7, "No active assignments"
            );
        }

        assigned.forEach(item => {
            const row = document.createElement("tr");

            addCell(row, item.request_id);
            addCell(row, item.supplier_name);
            addCell(row, item.location);
            addCell(row, item.quantity_kg + " kg");
            addCell(row, item.requested_date);

            const statusCell = addCell(row, "");
            const badge = document.createElement("span");
            badge.className = "status assigned";
            badge.textContent = "Assigned";
            statusCell.appendChild(badge);

            const actionCell = addCell(row, "");
            const button = document.createElement("button");
            button.type = "button";
            button.className = "action-btn";
            button.textContent = "Complete Collection";

            button.addEventListener("click", () => {
                completeCollection(item.request_id, button);
            });

            actionCell.appendChild(button);
            assignmentTable.appendChild(row);
        });

        if (collected.length === 0) {
            showEmpty(
                completedTable, 4, "No completed collections"
            );
        }

        collected.forEach(item => {
            const row = document.createElement("tr");
            addCell(row, item.request_id);
            addCell(row, item.supplier_name);
            addCell(row, item.quantity_kg + " kg");

            const statusCell = addCell(row, "");
            const badge = document.createElement("span");
            badge.className = "status collected";
            badge.textContent = "Collected";
            statusCell.appendChild(badge);

            completedTable.appendChild(row);
        });

    } catch (error) {
        collectorMessage.textContent = error.message;
    }
}

async function completeCollection(requestId, button) {
    const confirmed = window.confirm(
        "Have you collected this fish waste?"
    );

    if (!confirmed) return;

    button.disabled = true;
    collectorMessage.textContent = "Updating collection...";

    try {
        const response = await fetch(
            `/api/collector/collections/${requestId}/complete`,
            { method: "POST" }
        );

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Update failed");
        }

        await loadAssignments();
        collectorMessage.textContent = result.message;

    } catch (error) {
        collectorMessage.textContent = error.message;
        button.disabled = false;
    }
}

loadAssignments();
