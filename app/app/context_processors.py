from social.models import Author

def author_id(request):
    currentUser = request.user
    currentAuthor=False
    if currentUser.is_authenticated and Author.objects.filter(user=currentUser).exists():
        currentAuthor = Author.objects.filter(user=currentUser).get()
        currentAuthor = currentAuthor.id.split('/')[-1]
    return {'author_id': int(currentAuthor) if currentAuthor else 0}