// ccid校验是否存在
jQuery.validator.addMethod('ccidCheck',
    function(value, element){
        var isSuccess = false;
        $.ajax({
            type: 'get',
            url: '/validate/ccid_exist/',
            data: {cuteid: value},
            async:false,
            dataType: 'json',
            success: function(data){
                isSuccess = data;
            }
    });
    return isSuccess;
    }, "ccid不存在。"
);