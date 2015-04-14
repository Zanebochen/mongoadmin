// 校验房间id是否存在
jQuery.validator.addMethod('roomidCheck',
    function(value, element){
        var isSuccess = false;
        $.ajax({
            type: 'get',
            url: '/validate/roomid_exist/',
            data: {roomid: value},
            async:false,
            dataType: 'json',
            success: function(data){
                isSuccess = data;
            }
    });
    return isSuccess;
    }, "房间id不存在。"
);