const perform_ajax_call = function (url, type, data, successCallback, errorCallback, beforeSendCallback,
                                    completeCallback, xcsrftokenval) {
    $.ajax({
        url: url,
        type: type,
        data: data,
        headers: {
            'X-CSRFToken': xcsrftokenval,
            'Content-Type': 'application/json'
        },
        success: successCallback,
        error: errorCallback,
        beforeSend: beforeSendCallback,
        complete: completeCallback
    });
}