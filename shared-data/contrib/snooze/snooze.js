/**
 * Adds the snooze tag to a message and calls the API to schedule the tag-removal
 * action
 * 
 * @function snooze
 */
function snooze() {
  const timeValue = $('#time-input').val();
  const selectValue = $('#time-select').val()
  
  // get message id
  const checkboxes = $("input[name='mid']:checked");
  
  if (timeValue && checkboxes && checkboxes.length > 0) {
    const time = parseInt(timeValue) * parseInt(selectValue);
    console.log( "hallo", time)
    const checkbox = checkboxes[0];
    // the message ID
    const id = $(checkbox).val();
    
    // snooze tag is added
    $.ajax({
      url			 : Mailpile.api.tag,
      type		 : 'POST',
      data     : {
        csrf: Mailpile.csrf_token,
        add: 'snooze',
        del: 'inbox',
        mid: [id]
      },
      dataType : 'json',
      success  : function(response) {
        location.reload().then(() => {
          // display notification
          if (response.status == 'success') {
            Mailpile.notification({status: 'info', message: 'Message Snoozed'}); 
          } else {
            Mailpile.notification(response);
          }
        })  
      }
    });    
    
    // schedule the untagging task
    const url = `/snooze/${id}/${time}/`;
    $.ajax({
      url,
      type		: 'GET',
      dataType: 'json',
      success	: function(result) {
        return;       
      },
    });
  }  
  Mailpile.UI.hide_modal();
  checkboxes.each(box => $(box).prop('checked', false));
}

// Display the snooze dialog
$(document).on('click', '.bulk-action-snooze', function() {
  var $context = $(this);
  Mailpile.API.with_template('snooze-modal', function(modal) {
    mf = $('#modal-full').html(modal({
      context: $('#search-query').data('context')
    }));

    mf.modal(Mailpile.UI.ModalOptions);    
  });
});

// expose the method
return {
  'snooze': snooze
}
