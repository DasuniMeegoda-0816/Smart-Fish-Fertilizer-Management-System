async function loadFertilizers() {
    const container = document.getElementById("fertilizerList");
    const productCount = document.getElementById("productCount");

    try {
        const response = await fetch("/api/fertilizers");

        if (!response.ok) {
            throw new Error("Unable to load fertilizers");
        }

        const products = await response.json();

        container.replaceChildren();
        productCount.textContent = products.length;

        if (products.length === 0) {
            container.textContent = "No fertilizers available.";
            return;
        }

        products.forEach(product => {
            const card = document.createElement("div");
            card.className = "product-card";

            const icon = document.createElement("div");
            icon.className = "product-icon";
            icon.textContent = "🌱";

            const title = document.createElement("h3");
            title.textContent = product.fertilizer_name;

            const price = document.createElement("p");
            price.className = "product-price";
            price.textContent = `Rs. ${product.price} / kg`;

            const stock = document.createElement("p");
            stock.textContent = `Available stock: ${product.stock_kg} kg`;

            card.append(icon, title, price, stock);
            container.appendChild(card);
        });

    } catch (error) {
        container.textContent = error.message;
    }
}

loadFertilizers();


/* LOAD PRODUCTS INTO FARMER ORDER FORM */

async function loadOrderFertilizers() {
    const select = document.getElementById("orderFertilizer");

    if (!select) return;

    try {
        const response = await fetch("/api/fertilizers");

        if (!response.ok) {
            throw new Error("Cannot load fertilizers");
        }

        const products = await response.json();

        select.replaceChildren();

        const placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = "Select Fertilizer";
        select.appendChild(placeholder);

        products.forEach(product => {
            const option = document.createElement("option");

            option.value = product.fertilizer_id;
            option.textContent =
                `${product.fertilizer_name} - Rs. ${product.price}/kg`;

            option.disabled = Number(product.stock_kg) <= 0;

            select.appendChild(option);
        });

    } catch (error) {
        const message = document.getElementById("orderMessage");

        if (message) {
            message.textContent = error.message;
        }
    }
}

document.addEventListener("DOMContentLoaded", () => {
    loadOrderFertilizers();
});

/* FARMER ORDER SUBMISSION */

function initializeFarmerOrderForm() {
    const form = document.getElementById("farmerOrderForm");
    const message = document.getElementById("orderMessage");

    if (!form || !message) return;

    form.addEventListener("submit", async function(event) {
        event.preventDefault();

        const fertilizerId =
            document.getElementById("orderFertilizer").value;

        const quantity =
            document.getElementById("orderQuantity").value;

        const button = form.querySelector(
            'button[type="submit"]'
        );

        if (!fertilizerId || !quantity || Number(quantity) <= 0) {
            message.textContent = "Please enter valid order details";
            return;
        }

        button.disabled = true;
        message.textContent = "Processing your order...";

        try {
            const response = await fetch("/api/farmer/orders", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    fertilizer_id: Number(fertilizerId),
                    quantity_kg: quantity
                })
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(
                    result.error || "Order submission failed"
                );
            }

            form.reset();

            message.textContent =
                `Order #${result.order_id} placed successfully!`;

            if (typeof loadFertilizers === "function") {
                await loadFertilizers();
            }

            if (typeof loadOrderFertilizers === "function") {
                await loadOrderFertilizers();
            }

        } catch (error) {
            message.textContent = error.message;
            console.error("Order error:", error);

        } finally {
            button.disabled = false;
        }
    });
}

if (document.readyState === "loading") {
    document.addEventListener(
        "DOMContentLoaded",
        initializeFarmerOrderForm
    );
} else {
    initializeFarmerOrderForm();
}

async function loadMyOrders() {
    const table = document.getElementById("myOrdersTable");
    if (!table) return;

    try {
        const response = await fetch("/api/farmer/my-orders");

        if (!response.ok) {
            throw new Error("Cannot load orders");
        }

        const orders = await response.json();
        table.replaceChildren();

        if (orders.length === 0) {
            const row = document.createElement("tr");
            const cell = document.createElement("td");
            cell.colSpan = 6;
            cell.textContent = "No orders found";
            row.appendChild(cell);
            table.appendChild(row);
            return;
        }

        orders.forEach(order => {
            const row = document.createElement("tr");

            [
                order.order_id,
                order.fertilizer_name,
                `${order.quantity_kg} kg`,
                `Rs. ${(order.quantity_kg * order.price).toFixed(2)}`,
                order.created_at.slice(0, 10),
                order.status
            ].forEach(value => {
                const cell = document.createElement("td");
                cell.textContent = value;
                row.appendChild(cell);
            });

            table.appendChild(row);
        });

    } catch (error) {
        table.replaceChildren();
        const row = document.createElement("tr");
        const cell = document.createElement("td");
        cell.colSpan = 6;
        cell.textContent = error.message;
        row.appendChild(cell);
        table.appendChild(row);
    }
}

loadMyOrders();
