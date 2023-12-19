#!/bin/bash

for i in {1..50}; do
  curl 'http://localhost:8000/api/pipeline/call' \
    -H 'Cache-Control: no-cache' \
    -H 'Content-Type: application/json' \
    -H 'Authorization: Bearer EMPTYEMPTYEMPTYEMPTYEMPTYEMPTYEMPTYEMPTY' \
    -H 'Origin: http://localhost:8000' \
    --data-raw '{"pipeline_id":19,"openaikey_id":"2","args":{"smth":"print(1)"}}' \
    --compressed >"response_$i.txt" &
done

wait
