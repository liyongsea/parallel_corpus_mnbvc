chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.type === "getApiKey") {
      chrome.storage.sync.get("openaiApiKey", (data) => {
        sendResponse({ apiKey: data.openaiApiKey });
      });
      return true; // Required to use sendResponse asynchronously
    }
    else if (request.type === "getUrl"){
      chrome.storage.sync.get("otherService", (data) => {
        sendResponse({ otherServiceUrl: data.otherService });
      });
      return true; // Required to use sendResponse asynchronously
    }
    else if(request.type === "getChecked"){
      chrome.storage.sync.get("checked", (data) => {
        sendResponse({ checked: data.checked });
      });
      return true; // Required to use sendResponse asynchronously
    }
  });
  