import Vue from "vue/dist/vue.esm";
import AxiosConfig from "axios";

let headers = {"Content-Type": "application/json",
               "Accept": "application/json"};
const csrf_el = document.querySelector("meta[name=csrf-token]");
if(csrf_el) headers["X-CSRF-Token"] = csrf_el.getAttribute("content");

const Axios = AxiosConfig.create({headers: headers});

// Add method override to request
Axios.interceptors.request.use(config => {
  const method = config.method.toUpperCase();
  if (["PUT", "DELETE", "PATCH"].includes(method)) {
    config.headers = {
      ...config.headers,
      ["X-HTTP-Method-Override"]: method,
    };
    config.method = "post";
  }
  return config;
});

export default Axios;
