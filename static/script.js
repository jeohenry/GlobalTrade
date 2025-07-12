function showModal(type) {
  document.getElementById("modalTitle").innerText = type + " Investment";
  document.getElementById("investmentModal").style.display = "block";
}

function closeModal() {
  document.getElementById("investmentModal").style.display = "none";
}

// Reveal admin panel with secret key (Ctrl + A)
document.addEventListener('keydown', function(e) {
  if (e.ctrlKey && e.key === 'a') {
    document.getElementById("adminSection").style.display = 'block';
  }
});

async function fetchCryptoPrices() {
  const res = await fetch('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,usdt&vs_currencies=usd');
  const data = await res.json();
  document.getElementById("cryptoPrices").innerHTML = `
    <p>Bitcoin (BTC): $${data.bitcoin.usd}</p>
    <p>Ethereum (ETH): $${data.ethereum.usd}</p>
    <p>Tether (USDT): $${data.usdt.usd}</p>
  `;
}
fetchCryptoPrices();
setInterval(fetchCryptoPrices, 60000); // Refresh every minute

const ctx = document.getElementById('investmentChart').getContext('2d');
const investmentChart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6', 'Day 7'],
    datasets: [
      {
        label: 'Stocks & Bonds',
        data: [100, 118, 136, 130, 175, 181, 193],
        borderColor: 'blue',
        fill: false
      },
      {
        label: 'Real Estate',
        data: [100, 114, 129, 130, 158, 176, 166],
        borderColor: 'green',
        fill: false
      },
      {
        label: 'Crypto Portfolios',
        data: [100, 110, 120, 135, 165, 180, 200],
        borderColor: 'orange',
        fill: false
      }
    ]
  },
  options: {
    responsive: true,
    scales: {
      y: {
        beginAtZero: false,
        title: {
          display: true,
          text: 'Investment Value ($)'
        }
      },
      x: {
        title: {
          display: true,
          text: 'Days'
        }
      }
    }
  }
});