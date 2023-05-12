const perform_ajax_call = function (url, type, data, successCallback, errorCallback, beforeSendCallback,
                                    completeCallback, xcsrftoken) {
    $.ajax({
        url: url,
        type: type,
        data: data,
        headers: {
            'X-CSRFToken': xcsrftoken,
            'Content-Type': 'application/json'
        },
        success: successCallback,
        error: errorCallback,
        beforeSend: beforeSendCallback,
        complete: completeCallback
    });
}