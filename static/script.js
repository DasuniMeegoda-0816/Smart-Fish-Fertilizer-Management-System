const wasteForm = document.getElementById("wasteForm");
const orderForm = document.getElementById("orderForm");
const messageBox = document.getElementById("message");
function showMessage(msg) { messageBox.textContent = msg; }

async function loadWaste() {
  try {
    const response = await fetch("/api/waste");
    if (!response.ok) throw new Error("Cannot load waste records");
    const records = await response.json();
    const list = document.getElementById("wasteList");
    list.replaceChildren();
    records.forEach(item => {
      const li = document.createElement("li");
      li.textContent = `${item.supplier_name} - ${item.location} - ${item.quantity_kg} kg (${item.status})`;
      list.appendChild(li);
    });
  } catch (error) { showMessage(error.message); }
}

wasteForm.addEventListener("submit", async event => {
  event.preventDefault();
  const data = {
    supplier_name: document.getElementById("supplierName").value,
    location: document.getElementById("location").value,
    quantity_kg: document.getElementById("wasteQuantity").value
  };
  try {
    const response = await fetch("/api/waste", {
      method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(data)
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Submission failed");
    showMessage(result.message);
    wasteForm.reset();
    await loadWaste();
  } catch (error) { showMessage(error.message); }
});

async function loadFertilizers() {
  try {
    const response = await fetch("/api/fertilizers");
    if (!response.ok) throw new Error("Cannot load fertilizers");
    const fertilizers = await response.json();
    const select = document.getElementById("fertilizer");
    select.replaceChildren();
    fertilizers.forEach(item => {
      const option = document.createElement("option");
      option.value = item.fertilizer_id;
      option.textContent = `${item.fertilizer_name} - Rs. ${item.price}/kg (Stock: ${item.stock_kg} kg)`;
      select.appendChild(option);
    });
  } catch (error) { showMessage(error.message); }
}

orderForm.addEventListener("submit", async event => {
  event.preventDefault();
  const data = {
    farmer_name: document.getElementById("farmerName").value,
    fertilizer_id: document.getElementById("fertilizer").value,
    quantity_kg: document.getElementById("orderQuantity").value
  };
  try {
    const response = await fetch("/api/orders", {
      method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(data)
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Order failed");
    showMessage(result.message);
    orderForm.reset();
    await loadFertilizers();
  } catch (error) { showMessage(error.message); }
});

loadWaste();
loadFertilizers();
