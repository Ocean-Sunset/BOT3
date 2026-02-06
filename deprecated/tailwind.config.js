/** @type {import('tailwindcss').Config} */
module.exports = {
content: [
'./*.html',
'./src/**/*.js'
],
theme: {
extend: {
colors: {
mantraBlue: '#4EA8F0',
mantraPurple: '#7B61FF',
mantraBlack: '#0b0f17'
},
backgroundImage: {
'mantra-grad': 'linear-gradient(180deg, rgba(78,168,240,0.08), rgba(123,97,255,0.06))'
}
}
},
plugins: []
}