
const wasteList = document.getElementById("wasteList");
const inventoryList = document.getElementById("inventoryList");
const receiptSelect = document.getElementById("receiptId");
const fertilizerSelect = document.getElementById("fertilizerId");
const productionForm = document.getElementById("productionForm");
const message = document.getElementById("message");

async function api(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "Request failed");
    }

    return data;
}

function makeCard(title, description, action) {
    const card = document.createElement("article");
    card.className = "item-card";

    const heading = document.createElement("h3");
    heading.textContent = title;

    const paragraph = document.createElement("p");
    paragraph.textContent = description;

    card.append(heading, paragraph);

    if (action) {
        card.appendChild(action);
    }

    return card;
}

function addOption(select, value, label) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.appendChild(option);
}

async function loadProducerData() {
    try {
        const [waste, receipts, fertilizers] = await Promise.all([
            api("/api/producer/waste"),
            api("/api/producer/receipts"),
            api("/api/producer/fertilizers")
        ]);

        wasteList.replaceChildren();
        inventoryList.replaceChildren();
        receiptSelect.replaceChildren();
        fertilizerSelect.replaceChildren();

        addOption(receiptSelect, "", "Select Received Waste");
        addOption(fertilizerSelect, "", "Select Fertilizer");

        document.getElementById("wasteCount").textContent =
            waste.length;

        document.getElementById("productCount").textContent =
            fertilizers.length;

        // Completed production batches are not returned by
        // these APIs, so this counter is left as a placeholder.
        document.getElementById("batchCount").textContent = "—";

        if (waste.length === 0) {
            wasteList.textContent = "No collected waste available";
        }

        waste.forEach(item => {
            const button = document.createElement("button");
            button.textContent = "Receive Waste";

            button.addEventListener("click", async () => {
                button.disabled = true;

                try {
                    const result = await api(
                        "/api/producer/receive",
                        {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json"
                            },
                            body: JSON.stringify({
                                waste_id: item.waste_id
                            })
                        }
                    );

                    message.textContent = result.message;
                    await loadProducerData();

                } catch (error) {
                    message.textContent = error.message;
                    button.disabled = false;
                }
            });

            wasteList.appendChild(makeCard(
                `Fish Waste #${item.waste_id}`,
                `${item.quantity_kg} kg – ${item.location}`,
                button
            ));
        });

        receipts.forEach(item => {
            addOption(
                receiptSelect,
                item.receipt_id,
                `Receipt #${item.receipt_id} – ${item.quantity_kg} kg`
            );
        });

        fertilizers.forEach(item => {
            addOption(
                fertilizerSelect,
                item.fertilizer_id,
                item.fertilizer_name
            );

            inventoryList.appendChild(makeCard(
                item.fertilizer_name,
                `Stock: ${item.stock_kg} kg | Rs. ${item.price}/kg`
            ));
        });

    } catch (error) {
        message.textContent = error.message;
    }
}

productionForm.addEventListener("submit", async event => {
    event.preventDefault();

    const data = {
        receipt_id: receiptSelect.value,
        fertilizer_id: fertilizerSelect.value,
        quantity_kg: document.getElementById("quantity").value
    };

    try {
        const result = await api("/api/producer/production", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(data)
        });

        productionForm.reset();
        message.textContent = result.message;

        await loadProducerData();

    } catch (error) {
        message.textContent = error.message;
    }
});

loadProducerData();

