
const requestTable = document.getElementById("collectionTable");
const requestSelect = document.getElementById("requestId");
const collectorSelect = document.getElementById("collectorId");
const assignForm = document.getElementById("assignForm");
const assignMessage = document.getElementById("assignMessage");

function addOption(select, value, label) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.appendChild(option);
}

async function fetchJSON(url, options) {
    const response = await fetch(url, options);
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "Request failed");
    }

    return data;
}

async function loadAdminData() {
    try {
        const requests = await fetchJSON("/api/admin/collections");
        const collectors = await fetchJSON("/api/admin/collectors");

        requestTable.replaceChildren();
        requestSelect.replaceChildren();
        collectorSelect.replaceChildren();

        addOption(requestSelect, "", "Select Pending Request");
        addOption(collectorSelect, "", "Select Waste Collector");

        document.getElementById("totalRequests").textContent =
            requests.length;

        document.getElementById("pendingRequests").textContent =
            requests.filter(r => r.status === "Pending").length;

        document.getElementById("assignedRequests").textContent =
            requests.filter(r => r.status === "Assigned").length;

        document.getElementById("collectedRequests").textContent =
            requests.filter(r => r.status === "Collected").length;

        requests.forEach(item => {
            const row = document.createElement("tr");

            const values = [
                item.request_id,
                item.supplier_name,
                item.location,
                `${item.quantity_kg} kg`,
                item.requested_date,
                item.status
            ];

            values.forEach(value => {
                const cell = document.createElement("td");
                cell.textContent = value;
                row.appendChild(cell);
            });

            requestTable.appendChild(row);

            if (item.status === "Pending") {
                addOption(
                    requestSelect,
                    item.request_id,
                    `Request #${item.request_id} - ${item.location}`
                );
            }
        });

        if (requests.length === 0) {
            const row = document.createElement("tr");
            const cell = document.createElement("td");
            cell.colSpan = 6;
            cell.textContent = "No collection requests";
            row.appendChild(cell);
            requestTable.appendChild(row);
        }

        collectors.forEach(collector => {
            addOption(
                collectorSelect,
                collector.user_id,
                collector.full_name
            );
        });

    } catch (error) {
        assignMessage.textContent = error.message;
    }
}

assignForm.addEventListener("submit", async event => {
    event.preventDefault();

    const requestId = requestSelect.value;
    const collectorId = collectorSelect.value;

    try {
        const result = await fetchJSON(
            `/api/admin/collections/${requestId}/assign`,
            {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    collector_id: collectorId
                })
            }
        );

        assignMessage.textContent = result.message;
        await loadAdminData();

    } catch (error) {
        assignMessage.textContent = error.message;
    }
});

loadAdminData();

async function loadAdminFarmerOrders() {
    const table = document.getElementById("adminFarmerOrders");
    const message = document.getElementById("adminOrderMessage");

    if (!table || !message) return;

    table.replaceChildren();

    try {
        const response = await fetch("/api/admin/farmer-orders");

        if (!response.ok) throw new Error("Cannot load orders");

        const orders = await response.json();

        if (orders.length === 0) {
            const row = table.insertRow();
            const cell = row.insertCell();
            cell.colSpan = 6;
            cell.textContent = "No farmer orders";
            return;
        }

        orders.forEach(order => {
            const row = table.insertRow();

            [
                order.order_id,
                order.farmer_name,
                order.fertilizer_name,
                `${order.quantity_kg} kg`,
                order.status
            ].forEach(value => {
                const cell = row.insertCell();
                cell.textContent = value;
            });

            const actionCell = row.insertCell();

            let nextStatus = null;

            if (order.status === "Pending") {
                nextStatus = "Processing";
            } else if (order.status === "Processing") {
                nextStatus = "Delivered";
            }

            if (nextStatus) {
                const button = document.createElement("button");
                button.textContent = `Mark ${nextStatus}`;

                button.addEventListener("click", async () => {
                    button.disabled = true;

                    try {
                        const res = await fetch(
                            `/api/admin/farmer-orders/${order.order_id}/status`,
                            {
                                method: "POST",
                                headers: {
                                    "Content-Type": "application/json"
                                },
                                body: JSON.stringify({
                                    status: nextStatus
                                })
                            }
                        );

                        const result = await res.json();

                        if (!res.ok) {
                            throw new Error(
                                result.error || "Update failed"
                            );
                        }

                        message.textContent = result.message;
                        await loadAdminFarmerOrders();

                    } catch (error) {
                        message.textContent = error.message;
                        button.disabled = false;
                    }
                });

                actionCell.appendChild(button);
            } else {
                actionCell.textContent = "Completed";
            }
        });

    } catch (error) {
        message.textContent = error.message;
    }
}

if (document.readyState === "loading") {
    document.addEventListener(
        "DOMContentLoaded",
        loadAdminFarmerOrders
    );
} else {
    loadAdminFarmerOrders();
}
