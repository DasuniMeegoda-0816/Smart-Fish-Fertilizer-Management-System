const wasteForm = document.getElementById("supplierWasteForm");
const messageBox = document.getElementById("formMessage");
const tableBody = document.getElementById("wasteTableBody");

// Load the logged-in supplier's waste records
async function loadSupplierWaste() {
    try {
        const response = await fetch("/api/supplier/waste");

        if (!response.ok) {
            throw new Error("Cannot load waste records");
        }

        const records = await response.json();

        tableBody.replaceChildren();

        document.getElementById("totalRecords").textContent =
            records.length;

        const total = records.reduce(
            (sum, item) => sum + Number(item.quantity_kg), 0
        );

        document.getElementById("totalQuantity").textContent =
            total.toFixed(2) + " kg";

        document.getElementById("availableRecords").textContent =
            records.filter(item => item.status === "Available").length;

        if (records.length === 0) {
            const row = document.createElement("tr");
            const cell = document.createElement("td");
            cell.colSpan = 4;
            cell.textContent = "No waste records found";
            row.appendChild(cell);
            tableBody.appendChild(row);
            return;
        }

        records.forEach(item => {
            const row = document.createElement("tr");

            const values = [
                item.waste_id,
                item.location,
                item.quantity_kg + " kg",
                item.status
            ];

            values.forEach(value => {
                const cell = document.createElement("td");
                cell.textContent = value;
                row.appendChild(cell);
            });

            tableBody.appendChild(row);
        });

    } catch (error) {
        messageBox.textContent = error.message;
    }
}

// Register new fish waste
wasteForm.addEventListener("submit", async function(event) {
    event.preventDefault();

    const data = {
        location: document.getElementById("wasteLocation").value,
        quantity_kg: document.getElementById("wasteQuantity").value
    };

    try {
        const response = await fetch("/api/supplier/waste", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Registration failed");
        }

        messageBox.textContent = result.message;
        wasteForm.reset();

        await loadSupplierWaste();

    } catch (error) {
        messageBox.textContent = error.message;
    }
});

loadSupplierWaste();

const collectionForm =
    document.getElementById("collectionRequestForm");

const wasteSelect =
    document.getElementById("wasteSelect");

const collectionMessage =
    document.getElementById("collectionMessage");

const collectionTable =
    document.getElementById("collectionTableBody");

async function loadCollectionOptions() {
    const response = await fetch("/api/supplier/waste");

    if (!response.ok) {
        throw new Error("Cannot load waste records");
    }

    const records = await response.json();
     console.log("Collection dropdown records:", records);

    wasteSelect.replaceChildren();

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Select Waste Record";
    wasteSelect.appendChild(placeholder);

    records
        .filter(item => item.status === "Available")
        .forEach(item => {
            const option = document.createElement("option");

            option.value = item.waste_id;
            option.textContent =
                `Waste #${item.waste_id} - ${item.quantity_kg} kg`;

            wasteSelect.appendChild(option);
        });
}

async function loadCollectionRequests() {
    const response = await fetch("/api/supplier/collections");

    if (!response.ok) {
        throw new Error("Cannot load collection requests");
    }

    const requests = await response.json();

    collectionTable.replaceChildren();

    if (requests.length === 0) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");
        cell.colSpan = 4;
        cell.textContent = "No collection requests yet";
        row.appendChild(cell);
        collectionTable.appendChild(row);
        return;
    }

    requests.forEach(item => {
        const row = document.createElement("tr");

        [
            item.request_id,
            item.waste_id,
            item.requested_date,
            item.status
        ].forEach(value => {
            const cell = document.createElement("td");
            cell.textContent = value;
            row.appendChild(cell);
        });

        collectionTable.appendChild(row);
    });
}

collectionForm.addEventListener("submit", async event => {
    event.preventDefault();

    const data = {
        waste_id: wasteSelect.value,
        requested_date:
            document.getElementById("collectionDate").value
    };

    try {
        const response = await fetch("/api/supplier/collections", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Request failed");
        }

        collectionMessage.textContent = result.message;

        collectionForm.reset();

        await loadCollectionRequests();
        await loadCollectionOptions();

    } catch (error) {
        collectionMessage.textContent = error.message;
    }
});

async function initializeCollections() {
    try {
        await loadCollectionOptions();
        await loadCollectionRequests();
    } catch (error) {
        collectionMessage.textContent = error.message;
    }
}

initializeCollections();
