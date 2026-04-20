package main

import "net/http"

func main() {
	http.HandleFunc("/fail", func(w http.ResponseWriter, r *http.Request) { 
		w.WriteHeader(500) 
	})
	http.HandleFunc("/success", func(w http.ResponseWriter, r *http.Request) { 
		w.WriteHeader(200)
		w.Write([]byte("OK_FALLBACK")) 
	})
	http.ListenAndServe(":8081", nil)
}
