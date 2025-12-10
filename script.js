const API = "http://127.0.0.1:5000";

const chatEl = document.getElementById("chat");
const msgInput = document.getElementById("msg");
const sendBtn = document.getElementById("sendBtn");
const micBtn = document.getElementById("micBtn");
const offersEl = document.getElementById("offers");
const infoEl = document.getElementById("info");
const statusEl = document.getElementById("status");

sendBtn.onclick = sendMessage;
msgInput.addEventListener("keydown", (e)=>{ if(e.key==="Enter") sendMessage(); });

async function checkBackend(){
  try{
    const r = await fetch(API + "/");
    statusEl.textContent = "Backend: online";
  }catch(e){
    statusEl.textContent = "Backend: offline";
  }
}
checkBackend(); setInterval(checkBackend,5000);

function appendMessage(text,who="bot"){
  const div=document.createElement("div");
  div.className="msg "+(who==="user"?"user":"bot");
  div.innerHTML=`<div class="bubble">${text}</div>`;
  chatEl.appendChild(div);
  chatEl.scrollTop=chatEl.scrollHeight;
}

async function sendMessage(){
  const text=msgInput.value.trim(); if(!text) return;
  msgInput.value=""; appendMessage(text,"user"); appendMessage("...searching","bot");
  try{
    const res=await fetch(API+"/ai",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text})});
    const j=await res.json();
    const last=chatEl.querySelector(".msg.bot:last-child"); if(last && last.textContent.includes("...searching")) last.remove();
    appendMessage(j.reply,"bot");
    infoEl.innerHTML=`<div>Details present: <span class="details-indicator">${j.has_details?"Yes":"No"}</span></div>`;
    if(j.has_details) showOffers(j.details);
    speak(j.reply);
  }catch(e){ appendMessage("Error contacting backend","bot"); infoEl.innerHTML=`<div>Details present: <span class="details-indicator">No</span></div>`; }
}

function showOffers(items){
  offersEl.innerHTML=""; items.forEach(it=>{
    const div=document.createElement("div"); div.className="offer";
    div.innerHTML=`<img src="${it.image}"/><div class="meta"><strong>${it.name}</strong></div><button data-url="${it.platform_url}">Visit / Book</button>`;
    div.querySelector("button").onclick=()=>window.open(it.platform_url,"_blank");
    offersEl.appendChild(div);
  });
}

// TTS
function speak(text){ if(!window.speechSynthesis) return; const u=new SpeechSynthesisUtterance(text); u.lang="en-IN"; speechSynthesis.cancel(); speechSynthesis.speak(u); }

// STT
let recognition=null, listening=false;
if('webkitSpeechRecognition' in window || 'SpeechRecognition' in window){
  const Rec=window.SpeechRecognition||window.webkitSpeechRecognition;
  recognition=new Rec(); recognition.lang='en-IN'; recognition.interimResults=false;
  recognition.maxAlternatives=1;
  recognition.onresult=(e)=>{ msgInput.value=e.results[0][0].transcript; sendMessage(); }
  recognition.onend=()=>{listening=false; micBtn.textContent="🎤"; }
  recognition.onerror=()=>{listening=false; micBtn.textContent="🎤"; }
}
micBtn.onclick=()=>{
  if(!recognition) return alert("Use Chrome/Edge for voice support.");
  if(listening){ recognition.stop(); listening=false; micBtn.textContent="🎤"; }
  else { recognition.start(); listening=true; micBtn.textContent="⏺️"; }
};
