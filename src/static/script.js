$(document).ready(function(){
  $("a[name=like-button]").click(function(e){
      e.preventDefault();
      var value = $(this).attr("value");
      $(this).addClass('green');
      $("a[name=dislike-button").filter(function(){return this.value==value}).addClass('disabled');

      $.ajax({type: "POST",
            url: "/like/" + value,
            success:function(result){
            }
    });
  });
  $("a[name=dislike-button]").click(function(e){
      e.preventDefault();
      var value = $(this).attr("value");
      $(this).addClass('red');
      $("a[name=like-button").filter(function(){return this.value==value}).addClass('disabled');

      $.ajax({type: "POST",
            url: "/dislike/" + value,
            success:function(result){
            }
    });
  });
  $("a[name=save-button]").click(function(e){
      e.preventDefault();
      var value = $(this).attr("value");
      $.ajax({type: "POST",
            url: "/save/" + value,
            success:function(result){}
    });
  });
  $("a[name=delete-button]").click(function(e){
      e.preventDefault();
      var value = $(this).attr("value");
      $.ajax({type: "POST",
            url: "/delete/" + value,
            success:function(result){}
    });
  });
  $("a[name=update-button]").click(function(e){
      e.preventDefault();
      var path = window.location.pathname;
      if(path == '/'){
          path = '';
      }
      else{
          path = '/relevant'
      }
      $.ajax({type: "GET",
            url: path + "/update",
            success:function(result){
                window.location.reload();
            }
    });
  });
});
